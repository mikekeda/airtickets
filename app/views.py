from flask import render_template, jsonify, request, abort
from app import app, City, LanguageScript, CityName, Route, Airport, NeoAirport, NeoRoute
import os, sys
from sqlalchemy.orm import joinedload
from extensions import cache, redis_store, engine, db, es
from redis.exceptions import ConnectionError
import cPickle as pickle

BASE_TEMPLATES_DIR = os.path.dirname(os.path.abspath(__file__)) + '/templates'

# Context processors.


@app.context_processor
def select_parent_template():
    """Check if it's ajax, if so no need any parent template."""
    parent_template = "dummy_parent.html" if request.is_xhr else "base.html"
    return {'parent_template': parent_template}


@app.context_processor
def openshift():
    """Check if it's openshift."""
    return {'OPENSHIFT': ('OPENSHIFT_APP_NAME' in os.environ)}


# Routing.

@app.errorhandler(404)
def page_not_found(error):
    return render_template('page_not_found.html'), 404


@app.route('/ajax/')
@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@cache.cached(timeout=12 * 60 * 60)
@app.route('/ajax/autocomplete/cities')
def autocomplete_cities():
    """Autocomplete for cities."""
    query = request.args.get('query')

    redis_key = '|'.join(['autocomplete_cities', query])

    # Try to find with Redis.
    try:
        result = redis_store.get(redis_key)
        redis_is_connected = True
        if result:
            return pickle.loads(result)
    except ConnectionError:
        redis_is_connected = False

    # Try to find with Elasticsearch.
    try:
        cities = es.search(index='main-index', from_=0, size=10, doc_type='CityName', body= {
            "query": {
                "bool": {
                    "should": {
                        "match_phrase_prefix": {
                            'value.folded': {
                                'query': query,
                                'boost': 10
                            }
                        }
                    },
                    "must": {
                        "match_phrase_prefix": {
                            'value.folded': {
                                'query': query,
                                'fuzziness': 'AUTO'
                            }
                        },
                    }
                }
            }
        })
        result = jsonify(suggestions=[city['_source'] for city in cities['hits']['hits']])
        elasticsearch_is_connected = True
    except:
        elasticsearch_is_connected = False

    # Try to find with PostgreSQL.
    if not elasticsearch_is_connected:
        try:
            cities = CityName.query.options(joinedload(CityName.city)).filter(CityName.name.like(query + '%')).limit(10).all()
        except:
            db.session.close()
            engine.connect()
            cities = CityName.query.options(joinedload(CityName.city)).filter(CityName.name.like(query + '%')).limit(10).all()

        result = jsonify(suggestions=[city.autocomplete_serialize() for city in cities])

    if redis_is_connected:
        redis_store.set(redis_key, pickle.dumps(result))

    return result


@cache.cached(timeout=12 * 60 * 60)
@app.route('/ajax/airports')
def airports():
    """Find closest airports."""
    lat = float(request.args.get('lat'))
    lng = float(request.args.get('lng'))
    limit = int(request.args.get('limit')) or 1

    redis_key = '|'.join(['airports', str(lat), str(lng), str(limit)])

    try:
        result = redis_store.get(redis_key)
        redis_is_connected = True
        if result:
            return pickle.loads(result)
    except ConnectionError:
        redis_is_connected = False

    result = jsonify(json_list=NeoAirport.get_closest_airports(lat, lng, limit))

    if redis_is_connected:
        redis_store.set(redis_key, pickle.dumps(result))

    return result


@cache.cached(timeout=12 * 60 * 60)
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
            return pickle.loads(result)
    except ConnectionError:
        redis_is_connected = False

    result = jsonify(routes=NeoRoute.get_path(from_airport, to_airport))

    if redis_is_connected:
        redis_store.set(redis_key, pickle.dumps(result))

    return result


# # Todo: impruve this
# @cache.cached(timeout=300) # is it work for json?
# @app.route('/ajax/get-cities/<ne_lng>/<ne_lat>/<sw_lng>/<sw_lat>/')
# def get_cities(ne_lng, ne_lat, sw_lng, sw_lat):
#     # supported_languages = LanguageScript.query.with_entities(LanguageScript.language_script).all()
#     # print supported_languages
#     # lang = request.accept_languages.best_match(supported_languages)
#     # print request.accept_languages
#     cities = City.query.options(joinedload(City.city_names)).filter(City.longitude < float(ne_lng)).\
#         filter(City.latitude < float(ne_lat)).\
#         filter(City.longitude > float(sw_lng)).\
#         filter(City.latitude > float(sw_lat)).limit(10).all()
#     return jsonify(json_list=[city.serialize() for city in cities])
