from collections import defaultdict
from functools import reduce
import math

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.sql import text

from app import db, engine


def _deg2rad(deg: float) -> float:
    """ Helper function that convert degrees to radians. """
    return deg * (math.pi / 180)


def get_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """ Get distance between two points. """
    radius = 6371  # radius of the earth in km
    d_lat = _deg2rad(lat2 - lat1)
    d_lon = _deg2rad(lon2 - lon1)
    dummy_a = math.sin(d_lat / 2) * math.sin(d_lat / 2) + \
        math.cos(_deg2rad(lat1)) * \
        math.cos(_deg2rad(lat2)) * \
        math.sin(d_lon / 2) * math.sin(d_lon / 2)
    dummy_c = 2 * math.atan2(math.sqrt(dummy_a), math.sqrt(1 - dummy_a))
    distance = radius * dummy_c  # distance in km

    return distance


class BaseModel(db.Model):
    __abstract__ = True

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = db.Column(db.Integer, primary_key=True)

    def save(self, commit=True):
        """ Save. """
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


class Airport(BaseModel):
    airport_name = db.Column(db.String(128))
    city = db.Column(db.String(128))
    country = db.Column(db.String(64))
    iata_faa = db.Column(db.String(4))
    icao = db.Column(db.String(10))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    timezone = db.Column(db.Float)
    dst = db.Column(db.String(1))
    tz_database_time_zone = db.Column(db.String())

    @staticmethod
    def get_closest_airports(lat: float, lng: float, limit: int = 1, offset: int = 0):
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
            "ORDER BY distance "
            "LIMIT :limit OFFSET :offset"
        )

        raw_data = conn.execute(s, latitude=lat, longitude=lng, limit=limit,
                                offset=offset).fetchall()

        return [dict(row) for row in raw_data]


class Route(BaseModel):
    source = db.Column(db.Integer, db.ForeignKey('airport.id'))
    destination = db.Column(db.Integer, db.ForeignKey('airport.id'))
    airline = db.Column(db.Integer, db.ForeignKey('airline.id'))
    distance = db.Column(db.Float)
    codeshare = db.Column(db.Boolean, default=False)
    equipment = db.Column(db.String)

    @staticmethod
    def get_path(source, destination):
        result = defaultdict(list)
        s = text("""
        WITH RECURSIVE search_graph(
            source, -- point 1
            destination, -- point 2
            distance, -- edge property
            depth, -- depth, starting from 1
            path -- path, stored using an array
        ) AS (
        SELECT -- ROOT node query
            g.source, -- point 1
            g.destination, -- point 2
            g.distance AS distance, -- edge property
            1 AS depth, -- initial depth =1
            ARRAY[g.source] AS path -- initial path
        FROM route AS g
        WHERE SOURCE = :source -- ROOT node =?
        UNION ALL SELECT -- recursive clause
            g.source, -- point 1
            g.destination, -- point 2
            g.distance + sg.distance AS distance, -- edge property
            sg.depth + 1 AS depth, -- depth + 1
            PATH || g.source AS PATH -- add a new point to the path
        FROM route AS g, search_graph AS sg -- circular INNER JOIN
        WHERE g.source = sg.destination -- recursive JOIN condition
            AND (g.source <> ALL(sg.path))-- prevent from cycling
            AND sg.depth <= 2 -- search depth =?
        )
        SELECT DISTINCT PATH || destination AS PATH,
                                depth,
                                distance
        FROM search_graph -- query a recursive table. You can add LIMIT output or use a cursor
        WHERE destination = :destination
        ORDER BY distance
        LIMIT 10
        """)

        conn = engine.connect()
        raw_data = conn.execute(s, source=source, destination=destination).fetchall()
        conn.close()

        needed_cities = list(reduce(lambda a, b: a | set(b['path']), raw_data, set()))
        airports = Airport.query.with_entities(
            Airport.id,
            Airport.airport_name,
            Airport.latitude,
            Airport.longitude,
        ).filter(Airport.id.in_(needed_cities)).all()
        airports = {
            airport.id: {
                'airport_name': airport.airport_name,
                'latitude': airport.latitude,
                'longitude': airport.longitude,
            }
            for airport in airports
        }

        for row in raw_data:
            result[row['depth']].append({
                'nodes': [airports[airport_id] for airport_id in row['path']],
                'total_distance': row['distance'],
            })

        return result


class City(BaseModel):
    __table_args__ = (
        db.UniqueConstraint('latitude', 'longitude', name='location'),
    )

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

        raw_data = conn.execute(s, latitude=lat, longitude=lng, limit=limit, offset=offset).fetchall()

        for raw_item in raw_data:
            item = {
                'id': raw_item['id'],
                'country_code': raw_item['country_code'],
                'data': {
                    'lat': raw_item['latitude'],
                    'lng': raw_item['longitude']
                },
                'population': raw_item['population'],
                'value': raw_item['name'],
                'distance': raw_item['distance']
            }
            result.append(item)

        conn.close()

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


class CityName(BaseModel):
    name = db.Column(db.String(128), index=True)
    lang = db.Column(db.String(16))
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=False)

    city = db.relationship('City', backref=db.backref('city'))

    def serialize(self):
        """ Serialize. """
        return {
            'name': self.name,
            'city_id': self.city_id,
        }

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
            '_index': 'airtickets-city-index',
            '_type': 'CityName',
            '_id': self.city_id,
            '_source': serialize_dict
        }


class Airline(BaseModel):
    name = db.Column(db.String(128))
    alias = db.Column(db.String(64))
    iata = db.Column(db.String(4))
    icao = db.Column(db.String(10))
    callsign = db.Column(db.String(64))
    country = db.Column(db.String(64))
    active = db.Column(db.Boolean, default=False)

    def serialize(self):
        """ Serialize. """
        return {
            'id': self.id,
            'name': self.name,
            'alias': self.alias,
            'iata': self.iata,
            'icao': self.icao,
            'callsign': self.callsign,
            'country': self.country,
            'active': self.active,
        }


db.create_all()
