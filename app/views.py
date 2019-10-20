import os
import pickle
import math

from elasticsearch.exceptions import (
    NotFoundError, ConnectionError as ElasticConnectionError
)
from flask import render_template, jsonify, request
from sqlalchemy.orm import joinedload
from redis.exceptions import ConnectionError as RedisConnectionError

from app import app, redis_store, es
from app.models import City, CityName, NeoAirport, NeoRoute

BASE_TEMPLATES_DIR = os.path.dirname(os.path.abspath(__file__)) + '/templates'


@app.context_processor
def select_parent_template():
    """ Check if it's ajax, if so no need any parent template. """
    parent_template = "dummy_parent.html" if request.is_xhr else "base.html"
    return {'parent_template': parent_template}


# Routing.

@app.errorhandler(404)
def page_not_found(_):
    return render_template('404.html'), 404


@app.route('/ajax/')
@app.route('/')
def index():
    """ Main page. """
    return render_template('index.html')


@app.route('/ajax/technologies')
@app.route('/technologies')
def technologies():
    """ About page. """
    return render_template('technologies.html')


@app.route('/ajax/autocomplete/cities')
def autocomplete_cities():
    """ Autocomplete for cities. """
    query = request.args.get('query')

    redis_key = '|'.join(['autocomplete_cities', query])

    # Try to find with Redis.
    try:
        result = redis_store.get(redis_key)
        redis_is_connected = True
        if result:
            return jsonify(suggestions=pickle.loads(result))
    except RedisConnectionError:
        redis_is_connected = False

    # Try to find with Elasticsearch.
    try:
        cities = es.search(
            index='airtickets-city-index',
            from_=0,
            size=10,
            doc_type='CityName',
            body={
                "query": {
                    "bool": {
                        "must": {
                            "match_phrase_prefix": {
                                "value": {
                                    "query": query
                                }
                            }
                        }
                    }
                },
                "sort": {
                    "population": {
                        "order": "desc"
                    }
                }
            }
        )
        result = [
            city['_source']
            for city in cities['hits']['hits']
        ]
    except (ElasticConnectionError, NotFoundError):
        # Try to find with PostgreSQL.
        cities = CityName.query.join(CityName.city)\
            .filter(CityName.name.like(query + '%'))\
            .order_by(City.population.desc())\
            .limit(10)\
            .all()

        result = [
            city.autocomplete_serialize()
            for city in cities
        ]

    if redis_is_connected:
        redis_store.set(redis_key, pickle.dumps(result), 86400)

    return jsonify(suggestions=result)


@app.route('/ajax/airports')
def airports():
    """ Find closest airports. """
    lat = float(request.args.get('lat'))
    lng = float(request.args.get('lng'))
    limit = int(request.args.get('limit')) or 1
    find_closest_city = request.args.get('find_closest_city') == 'true'

    redis_key = '|'.join(
        ['airports', str(lat), str(lng), str(limit), str(find_closest_city)]
    )

    try:
        result = redis_store.get(redis_key)
        redis_is_connected = True
        if result:
            return jsonify(pickle.loads(result))
    except RedisConnectionError:
        redis_is_connected = False

    result = {
        'airports': NeoAirport.get_closest_airports(lat, lng, limit)
    }

    if find_closest_city:
        # Try to find with Elasticsearch.
        try:
            cities = es.search(
                index='airtickets-city-index',
                from_=0,
                size=1,
                doc_type='CityName',
                body={
                    "query": {
                        "bool": {
                            "must": {
                                "geo_distance": {
                                    "distance": "500km",
                                    "location": {
                                        "lat": lat,
                                        "lon": lng
                                    }
                                }
                            }
                        }
                    },
                    "sort": {
                        "_geo_distance": {
                            "location": {
                                "lat": lat,
                                "lon": lng
                            },
                            "order": "asc",
                            "unit": "km"
                        }
                    },
                    "size": 1
                }
            )
            result['closest_city'] = cities['hits']['hits'][0]['_source']
        except (ElasticConnectionError, NotFoundError):
            result['closest_city'] = next(
                iter(City.get_closest_cities(lat, lng, 1) or []),
                None
            )

    if redis_is_connected:
        redis_store.set(redis_key, pickle.dumps(result), 86400)

    return jsonify(result)


@app.route('/ajax/routes')
def routes():
    """ Find routes between two airports. """
    from_airport = int(request.args.get('from_airport'))
    to_airport = int(request.args.get('to_airport'))

    redis_key = '|'.join(['routes', str(from_airport), str(to_airport)])

    try:
        result = redis_store.get(redis_key)
        redis_is_connected = True
        if result:
            return jsonify(routes=pickle.loads(result))
    except RedisConnectionError:
        redis_is_connected = False

    result = NeoRoute.get_path(from_airport, to_airport)

    if redis_is_connected:
        redis_store.set(redis_key, pickle.dumps(result), 86400)

    return jsonify(routes=result)


@app.route('/ajax/get-cities')
def get_cities():
    """ Get cities in specified area. """
    ne_lng = float(request.args.get('ne_lng'))
    ne_lat = float(request.args.get('ne_lat'))
    sw_lng = float(request.args.get('sw_lng'))
    sw_lat = float(request.args.get('sw_lat'))

    redis_key = '|'.join(
        ['get_cities', str(ne_lng), str(ne_lat), str(sw_lng), str(sw_lat)]
    )

    # Try to find with Redis.
    try:
        result = redis_store.get(redis_key)
        redis_is_connected = True
        if result:
            return jsonify(json_list=pickle.loads(result))
    except RedisConnectionError:
        redis_is_connected = False

    # Try to find with Elasticsearch.
    try:
        cities = es.search(
            index='airtickets-city-index',
            from_=0,
            size=10,
            doc_type='CityName',
            body={
                "query": {
                    "bool": {
                        "must": {
                            "geo_distance": {
                                "distance": str(NeoAirport.get_distance(
                                    ne_lat, ne_lng, sw_lat, sw_lng
                                ) / 2 / math.sqrt(2)) + 'km',
                                "location": {
                                    "lat": (ne_lat + sw_lat) / 2,
                                    "lon": (ne_lng + sw_lng) / 2
                                }
                            }
                        }
                    }
                },
                "sort": {
                    "population": {
                        "order": 'desc'
                    }
                }
            }
        )

        result = [{
            'city_names': [city['_source']['value']],
            'latitude': city['_source']['data']['lat'],
            'longitude': city['_source']['data']['lng'],
            'population': city['_source']['population']
        } for city in cities['hits']['hits']]
    except (ElasticConnectionError, NotFoundError):
        # Try to find with PostgreSQL.
        cities = City.query.options(joinedload(City.city_names))\
                     .filter(City.longitude < ne_lng)\
                     .filter(City.latitude < ne_lat)\
                     .filter(City.longitude > sw_lng)\
                     .filter(City.latitude > sw_lat)\
                     .order_by(City.population.desc())\
                     .limit(10)\
                     .all()

        result = [city.serialize() for city in cities]

    if redis_is_connected:
        redis_store.set(redis_key, pickle.dumps(result), 86400)

    return jsonify(json_list=result)
