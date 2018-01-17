import pickle
import math
import time

from sqlalchemy.sql import text
from sqlalchemy.orm import relationship, foreign, remote
from neomodel import (StructuredNode, StructuredRel, StringProperty,
                      IntegerProperty, FloatProperty, BooleanProperty,
                      RelationshipTo)
from neomodel import db as neomodel_db
from redis.exceptions import ConnectionError
from extensions import db, engine, redis_store


def _deg2rad(deg):
    """Helper function."""
    return deg * (math.pi / 180)


class PointMixin(object):
    def __repr__(self):
        return str(self.__dict__)

    @staticmethod
    def get_distance(lat1, lon1, lat2, lon2):
        """Get distance between two points."""
        radius = 6371  # Radius of the earth in km
        d_lat = _deg2rad(lat2 - lat1)
        d_lon = _deg2rad(lon2 - lon1)
        dummy_a = math.sin(d_lat / 2) * math.sin(d_lat / 2) + \
            math.cos(_deg2rad(lat1)) * \
            math.cos(_deg2rad(lat2)) * \
            math.sin(d_lon / 2) * math.sin(d_lon / 2)
        dummy_c = 2 * math.atan2(math.sqrt(dummy_a), math.sqrt(1 - dummy_a))
        distance = radius * dummy_c  # Distance in km
        return distance


class ModelMixin(object):
    def __repr__(self):
        return str(self.__dict__)

    def save(self):
        """Save."""
        db.session.add(self)
        db.session.commit()
        return self

    def get_or_create(self, model, **kwargs):
        """Get or create."""
        instance = db.session.query(model).filter_by(**kwargs).first()
        if instance:
            return instance, False

        instance = self.save()
        return instance, True


class NeoRoute(StructuredRel):
    airline = IntegerProperty()
    distance = FloatProperty()
    codeshare = BooleanProperty(default=False)
    equipment = StringProperty()
    departure_start = IntegerProperty(default=lambda: int(time.time()))
    departure_interval = IntegerProperty(default=86400)

    def __repr__(self):
        return '<NeoRoute {}>'.format(self.id)

    @staticmethod
    def get_path(from_airport, to_airport):
        """Get path from source_airport to destination_airport."""

        query = (
            "MATCH p=(startNode:NeoAirport)-[rels:{rel_type}*1..3]->"
            "(endNode:NeoAirport) "
            "WHERE id(startNode) = {from_airport} "
            "AND id(endNode) = {to_airport} "
            "RETURN p AS p, reduce(distance=0, r in rels | "
            "distance + r.distance) AS totalDistance "
            "ORDER BY totalDistance "
            "LIMIT 20"
        )

        query_data = {
            'from_airport': from_airport,
            'rel_type': 'AVAILABLE_DESTINATION',
            'to_airport': to_airport
        }

        query = query.format(**query_data)

        raw_data, _ = neomodel_db.cypher_query(query)

        result = {}

        for raw_item in raw_data:
            item = {
                'nodes': [node.properties for node in raw_item[0].nodes],
                'total_distance': raw_item[1]
            }

            result.setdefault(len(raw_item[0].nodes) - 2, []).append(item)

        return result


class NeoAirport(StructuredNode, PointMixin):
    airport_name = StringProperty()
    city = StringProperty()
    country = StringProperty()
    iata_faa = StringProperty(index=True)
    icao = StringProperty(index=True)
    latitude = FloatProperty()
    longitude = FloatProperty()
    altitude = FloatProperty()
    timezone = FloatProperty()
    dst = StringProperty()
    tz_database_time_zone = StringProperty()

    available_destinations = RelationshipTo(
        'NeoAirport', 'AVAILABLE_DESTINATION', model=NeoRoute
    )

    def __repr__(self):
        return '<NeoAirport {}>'.format(self.airport_name)

    @classmethod
    def category(cls):
        return "{}.nodes attribute".format(cls.__name__)

    def get_connections(self):
        results, _ = self.cypher(
            "START a=node({self}) MATCH a<-[:CONNECT]-(b) RETURN b"
        )
        return [self.__class__.inflate(row[0]) for row in results]

    @staticmethod
    def get_closest_airports(lat, lng, limit=1, distance=500, offset=0):
        """Get closest airports by coordinates."""
        query = ("CALL spatial.withinDistance('geom',{{latitude: {lat},"
                 "longitude: {lng}}}, {distance}) yield node, distance "
                 "RETURN DISTINCT node, distance "
                 "LIMIT {limit}")

        query_data = {
            'lat': lat,
            'lng': lng,
            'distance': float(distance),
            'offset': offset,
            'limit': limit
        }

        query = query.format(**query_data)
        raw_data, _ = neomodel_db.cypher_query(query)

        result = []

        for raw_item in raw_data:
            item = raw_item[0].properties
            item['id'] = raw_item[0].id
            item['distance'] = raw_item[1]

            result.append(item)

        return result

    def get_or_create(self, model, **kwargs):
        """Get or create."""
        instance = db.session.query(model).filter_by(**kwargs).first()
        if instance:
            return instance, False

        instance = self.save()
        return instance, True


class City(db.Model, ModelMixin):
    __tablename__ = 'city'
    id = db.Column(db.Integer, primary_key=True)
    country_code = db.Column(db.String(2))
    subdivision_code = db.Column(db.String(8))
    gns_fd = db.Column(db.String(8))
    gns_ufi = db.Column(db.Integer)
    language_code = db.Column(db.String(16))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    population = db.Column(db.Integer, default=0)

    city_names = db.relationship('CityName', backref=db.backref('city_names'))

    def __repr__(self):
        return '<City {}>'.format(self.id)

    def __init__(self, gns_ufi, latitude, longitude, country_code='US',
                 subdivision_code=51, gns_fd='PPL', language_code='en',
                 population=0):
        self.gns_ufi = gns_ufi
        self.latitude = latitude
        self.longitude = longitude
        self.country_code = country_code
        self.subdivision_code = subdivision_code
        self.gns_fd = gns_fd
        self.language_code = language_code
        self.population = population

    @staticmethod
    def get_closest_cities(lat, lng, limit=1, offset=0):
        """Get closest cities by coordinates."""

        redis_key = '|'.join(
            ['get_closest_cities', str(lat), str(lng), str(limit), str(offset)]
        )

        try:
            result = redis_store.get(redis_key)
            redis_is_connected = True
            if result:
                return pickle.loads(result)
        except ConnectionError:
            redis_is_connected = False

        result = []
        conn = engine.connect()

        s = text(
            "SELECT *, "
            "("
            "3959 * acos( cos( radians(:latitude) ) * "
            "cos( radians( latitude ) ) * cos( radians( longitude ) - "
            "radians(:longitude) ) + sin( radians(:latitude) ) * "
            "sin( radians( latitude ) ) )"
            ") AS distance "
            "FROM city "
            "INNER JOIN cityname ON cityname.city_id = city.id "
            "ORDER BY distance "
            "LIMIT :limit OFFSET :offset"
        )

        raw_data = conn.execute(s, latitude=lat, longitude=lng, limit=limit,
                                offset=offset).fetchall()

        for raw_item in raw_data:
            item = {
                'id': raw_item[0],
                'country_code': raw_item[1],
                'data': {
                    'lat': raw_item[6],
                    'lng': raw_item[7]
                },
                'population': raw_item[8],
                'value': raw_item[9],
                'distance': raw_item[12]
            }
            result.append(item)

        conn.close()
        if redis_is_connected:
            redis_store.set(redis_key, pickle.dumps(result))

        return result

    def serialize(self):
        """Serialize."""
        result = {
            'id': self.id,
            'gns_ufi': self.gns_ufi,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'country_code': self.country_code,
            'subdivision_code': self.subdivision_code,
            'gns_fd': self.gns_fd,
            'language_code': self.language_code,
            'population': self.population,
            'city_names': [name.name for name in self.city_names],
        }
        return result


class LanguageScript(db.Model, ModelMixin):
    __tablename__ = 'languagescript'
    id = db.Column(db.Integer, primary_key=True)
    language_script = db.Column(db.String(32), unique=True)

    city_names = db.relationship(
        'CityName',
        backref=db.backref('Languagescripts_city_names')
    )

    def __repr__(self):
        return '<Languagescript {}>'.format(self.language_script)

    def __init__(self, language_script='english'):
        self.language_script = language_script


class CityName(db.Model, ModelMixin):
    __tablename__ = 'cityname'
    name = db.Column(db.String(128))
    language_script_id = db.Column(
        db.Integer,
        db.ForeignKey('languagescript.id'),
        primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), primary_key=True)

    city = db.relationship('City', backref=db.backref('city'))

    def __repr__(self):
        return '<CityName {}>'.format(self.name)

    def __init__(self, name, language_script_id, city_id):
        self.name = name
        self.language_script_id = language_script_id
        self.city_id = city_id

    def serialize(self):
        """Serialize."""
        result = {
            'name': self.name,
            'city_id': self.city_id,
        }
        return result

    def autocomplete_serialize(self):
        """Serialize for autocomplete."""
        return {
            'value': self.name,
            'data': {
                'id': self.city.id,
                'lng': self.city.longitude,
                'lat': self.city.latitude,
                'country_code': self.city.country_code
            },
        }

    def elastic_serialize(self):
        """Serialize for Elastic."""
        serialize_dict = self.autocomplete_serialize()
        serialize_dict['location'] = {
            "lat": self.city.latitude,
            "lon": self.city.longitude
        }
        serialize_dict['population'] = getattr(self.city, 'population', 0)

        return {
            '_index': 'main-index',
            '_type': 'CityName',
            '_id': self.city_id,
            '_source': serialize_dict
        }


class Airport(db.Model, ModelMixin):
    __tablename__ = 'airport'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    city = db.Column(db.String(64))
    country = db.Column(db.String(64))
    iata_faa = db.Column(db.String(3))
    icao = db.Column(db.String(4))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    altitude = db.Column(db.Float)
    timezone = db.Column(db.Float)
    dst = db.Column(db.String(1))
    tz_database_time_zone = db.Column(db.String(64))

    routes_in = db.relationship('Route',
                                backref=db.backref('to_airport'),
                                foreign_keys='Route.destination_airport',
                                lazy='joined')
    routes_out = db.relationship('Route',
                                 backref=db.backref('from_airport'),
                                 foreign_keys='Route.source_airport',
                                 lazy='joined')

    def __repr__(self):
        return '<Airport {}>'.format(self.name)

    def __init__(self, name, city, country, iata_faa, icao, latitude,
                 longitude, altitude, timezone, dst, tz_database_time_zone):
        self.name = name
        self.city = city
        self.country = country
        self.iata_faa = iata_faa
        self.icao = icao
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude
        self.timezone = timezone
        self.dst = dst
        self.tz_database_time_zone = tz_database_time_zone

    def serialize(self):
        """Serialize."""
        result = {
            'id': self.id,
            'name': self.name,
            'city': self.city,
            'country': self.country,
            'iata_faa': self.iata_faa,
            'icao': self.icao,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude': self.altitude,
            'timezone': self.timezone,
            'dst': self.dst,
            'tz_database_time_zone': self.tz_database_time_zone,
        }
        return result

    @staticmethod
    def get_closest_airports(lat, lng, limit=1, offset=0):
        """Get closest airports by coordinates."""

        redis_key = '|'.join(
            [
                'get_closest_airports',
                str(lat),
                str(lng),
                str(limit),
                str(offset)
            ]
        )
        result = redis_store.get(redis_key)

        if result:
            return pickle.loads(result)

        result = []
        conn = engine.connect()

        s = text(
            "SELECT *, "
            "("
            "3959 * acos( cos( radians(:latitude) ) * "
            "cos( radians( latitude ) ) * cos( radians( longitude ) - "
            "radians(:longitude) ) + sin( radians(:latitude) ) * "
            "sin( radians( latitude ) ) )"
            ") AS distance "
            "FROM airport "
            "WHERE id IN (SELECT source_airport FROM route) "
            "OR id IN (SELECT destination_airport FROM route) "
            "ORDER BY distance "
            "LIMIT :limit OFFSET :offset"
        )

        raw_data = conn.execute(s, latitude=lat, longitude=lng, limit=limit,
                                offset=offset).fetchall()

        for raw_item in raw_data:
            item = {
                'id': raw_item[0],
                'name': raw_item[1],
                'city': raw_item[2],
                'country': raw_item[3],
                'iata_faa': raw_item[4],
                'icao': raw_item[5],
                'latitude': raw_item[6],
                'longitude': raw_item[7],
                'altitude': raw_item[8],
                'timezone': raw_item[9],
                'dst': raw_item[10],
                'tz_database_time_zone': raw_item[11],
                'distance': raw_item[12],
            }
            result.append(item)

        conn.close()
        redis_store.set(redis_key, pickle.dumps(result))

        return result


class Airline(db.Model, ModelMixin):
    __tablename__ = 'airline'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    alias = db.Column(db.String(64))
    iata = db.Column(db.String(4))
    icao = db.Column(db.String(10))
    callsign = db.Column(db.String(64))
    country = db.Column(db.String(64))
    active = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<Airline {}>'.format(self.name)

    def __init__(self, name, alias, iata, icao, callsign, country,
                 active=False):
        self.name = name
        self.alias = alias
        self.iata = iata
        self.icao = icao
        self.callsign = callsign
        self.country = country
        self.active = active

    def serialize(self):
        """Serialize."""
        result = {
            'id': self.id,
            'name': self.name,
            'alias': self.alias,
            'iata': self.iata,
            'icao': self.icao,
            'callsign': self.callsign,
            'country': self.country,
            'active': self.active,
        }
        return result


class Route(db.Model, ModelMixin):
    __tablename__ = 'route'
    id = db.Column(db.Integer, primary_key=True)
    airline = db.Column(db.Integer, db.ForeignKey('airline.id'))
    source_airport = db.Column(db.Integer, db.ForeignKey('airport.id'))
    destination_airport = db.Column(db.Integer, db.ForeignKey('airport.id'))
    codeshare = db.Column(db.Boolean, default=False)
    equipment = db.Column(db.String(48))

    next_routes = relationship(
        "Route",
        primaryjoin=remote(foreign(source_airport)) == destination_airport
    )

    def __repr__(self):
        return '<Route {}>'.format(self.id)

    def __init__(self, airline, source_airport, destination_airport, codeshare,
                 equipment):
        self.airline = airline
        self.source_airport = source_airport
        self.destination_airport = destination_airport
        self.codeshare = codeshare
        self.equipment = equipment

    def serialize(self):
        """Serialize."""
        result = {
            'id': self.id,
            'airline': self.airline,
            'source_airport': self.source_airport,
            'destination_airport': self.destination_airport,
            'codeshare': self.codeshare,
            'equipment': self.equipment,
            'from_airport': self.from_airport.serialize(),
            'to_airport': self.to_airport.serialize(),
        }
        return result

    def serialize_with_next_routes(self, destination):
        """Serialize."""
        result = self.serialize()
        result['next_routes'] = [
            route.serialize()
            for route in self.next_routes
            if route.destination_airport == destination
        ]
        return result


db.create_all()
