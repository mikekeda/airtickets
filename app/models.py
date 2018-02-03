import pickle
import math
import time

from sqlalchemy.sql import text
from neomodel import (StructuredNode, StructuredRel, StringProperty,
                      IntegerProperty, FloatProperty, BooleanProperty,
                      RelationshipTo)
from neomodel import db as neomodel_db
from redis.exceptions import ConnectionError as RedisConnectionError

from app import db, engine, redis_store


def _deg2rad(deg):
    """ Helper function that convert degrees to radians. """
    return deg * (math.pi / 180)


class PointMixin(object):
    @staticmethod
    def get_distance(lat1, lon1, lat2, lon2):
        """ Get distance between two points. """
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
    def save(self, commit=True):
        """Save."""
        db.session.add(self)
        if commit:
            db.session.commit()
        return self

    @classmethod
    def get_or_create(cls, defaults=None, commit=True, **kwargs):
        """ Get or create. """
        obj = db.session.query(cls).filter_by(**kwargs).first()
        created = False
        if not obj:
            kwargs = dict(kwargs)
            if defaults:
                kwargs.update(defaults)
            obj = cls(**kwargs)
            obj.save(commit)
            created = True

        return obj, created


class NeoRoute(StructuredRel):
    airline = IntegerProperty()
    distance = FloatProperty()
    codeshare = BooleanProperty(default=False)
    equipment = StringProperty()
    departure_start = IntegerProperty(default=lambda: int(time.time()))
    departure_interval = IntegerProperty(default=86400)

    @staticmethod
    def get_path(from_airport, to_airport):
        """ Get path from source_airport to destination_airport. """

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
        """ Get closest airports by coordinates. """
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

    @staticmethod
    def get_closest_cities(lat, lng, limit=1, offset=0):
        """ Get closest cities by coordinates. """

        redis_key = '|'.join(
            ['get_closest_cities', str(lat), str(lng), str(limit), str(offset)]
        )

        try:
            result = redis_store.get(redis_key)
            redis_is_connected = True
            if result:
                return pickle.loads(result)
        except RedisConnectionError:
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
        """ Serialize. """
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


class CityName(db.Model, ModelMixin):
    __tablename__ = 'cityname'
    name = db.Column(db.String(128))
    language_script_id = db.Column(
        db.Integer,
        db.ForeignKey('languagescript.id'),
        primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), primary_key=True)
    city = db.relationship('City', backref=db.backref('city'))

    def serialize(self):
        """ Serialize. """
        result = {
            'name': self.name,
            'city_id': self.city_id,
        }
        return result

    def autocomplete_serialize(self):
        """ Serialize for autocomplete. """
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
        """ Serialize for Elastic. """
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

    def serialize(self):
        """ Serialize. """
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


db.create_all()
