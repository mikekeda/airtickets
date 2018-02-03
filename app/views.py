import os
import pickle
import math

from elasticsearch.exceptions import ConnectionError as ElasticConnectionError
from flask import render_template, jsonify, request
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import nullslast
from sqlalchemy import desc
from redis.exceptions import ConnectionError as RedisConnectionError

from app import app, City, CityName, NeoAirport, NeoRoute, cache, \
    redis_store, engine, db, es

BASE_TEMPLATES_DIR = os.path.dirname(os.path.abspath(__file__)) + '/templates'


@app.context_processor
def select_parent_template():
    """Check if it's ajax, if so no need any parent template."""
    parent_template = "dummy_parent.html" if request.is_xhr else "base.html"
    return {'parent_template': parent_template}


# Routing.

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


@app.route('/ajax/')
@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/ajax/technologies')
@app.route('/technologies')
def technologies():
    """About page."""
    return render_template('technologies.html')


@cache.cached(timeout=86400)
@app.route('/ajax/autocomplete/cities')
def autocomplete_cities():
    """Autocomplete for cities."""
    result = None
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
            index='main-index',
            from_=0,
            size=10,
            doc_type='CityName',
            body={
                "query": {
                    "bool": {
                        "should": {
                            "match_phrase_prefix": {
                                "value.folded": {
                                    "query": query,
                                    "boost": 10
                                }
                            }
                        },
                        "must": {
                            "match_phrase_prefix": {
                                "value.folded": {
                                    "query": query,
                                    "fuzziness": 'AUTO'
                                }
                            },
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
        result = [
            city['_source']
            for city in cities['hits']['hits']
        ]
        elasticsearch_is_connected = True
    except ElasticConnectionError:
        elasticsearch_is_connected = False

    # Try to find with PostgreSQL (reconnect to db if got an error).
    if not elasticsearch_is_connected:
        cities = CityName.query.options(joinedload(CityName.city))\
            .filter(CityName.name.like(query + '%'))\
            .order_by(nullslast(desc('population')))\
            .limit(10)\
            .all()

        result = [
            city.autocomplete_serialize()
            for city in cities
        ]

    if redis_is_connected:
        redis_store.set(redis_key, pickle.dumps(result), 86400)

    return jsonify(suggestions=result)


@cache.cached(timeout=86400)
@app.route('/ajax/airports')
def airports():
    """Find closest airports."""
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
                index='main-index',
                from_=0, size=1,
                doc_type='CityName',
                body={
                    "query": {
                        "filtered": {
                            "query": {
                                "match_all": {}
                            },
                            "filter": {
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
        except ElasticConnectionError:
            result['closest_city'] = next(
                iter(City.get_closest_cities(lat, lng, 1) or []),
                None
            )

    if redis_is_connected:
        redis_store.set(redis_key, pickle.dumps(result), 86400)

    return jsonify(result)


@cache.cached(timeout=86400)
@app.route('/ajax/routes')
def routes():
    """Find routes between two airports."""
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


@cache.cached(timeout=300)  # is it work for json?
@app.route('/ajax/get-cities')
def get_cities():
    # supported_languages = LanguageScript.query\
    #     .with_entities(LanguageScript.language_script).all()
    # print(supported_languages)
    # lang = request.accept_languages.best_match(supported_languages)
    # print request.accept_languages
    result = None
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
            index='main-index',
            from_=0, size=10,
            doc_type='CityName',
            body={
                "query": {
                    "filtered": {
                        "filter": {
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

        result = jsonify(json_list=[{
            'city_names': [city['_source']['value']],
            'latitude': city['_source']['data']['lat'],
            'longitude': city['_source']['data']['lng'],
            'population': city['_source']['population']
        } for city in cities['hits']['hits']])

        elasticsearch_is_connected = True
    except ElasticConnectionError:
        elasticsearch_is_connected = False

    # Try to find with PostgreSQL (reconnect to db if got an error).
    if not elasticsearch_is_connected:
        try:
            cities = City.query.options(joinedload(City.city_names))\
                         .filter(City.longitude < ne_lng)\
                         .filter(City.latitude < ne_lat)\
                         .filter(City.longitude > sw_lng)\
                         .filter(City.latitude > sw_lat)\
                         .order_by(nullslast(desc(City.population)))\
                         .limit(10)\
                         .all()
        except Exception:
            db.session.close()
            engine.connect()
            cities = City.query.options(joinedload(City.city_names))\
                         .filter(City.longitude < ne_lng)\
                         .filter(City.latitude < ne_lat)\
                         .filter(City.longitude > sw_lng)\
                         .filter(City.latitude > sw_lat)\
                         .order_by(nullslast(desc(City.population)))\
                         .limit(10)\
                         .all()

        result = [city.serialize() for city in cities]

    if redis_is_connected:
        redis_store.set(redis_key, pickle.dumps(result), 86400)

    return jsonify(json_list=result)
