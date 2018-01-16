import os
import requests

from neomodel import config

SITE_ENV_PREFIX = 'AIRTICKETS'


def get_env_var(name, default=''):
    """Get all sensitive data from google vm custom metadata."""
    try:
        name = '_'.join([SITE_ENV_PREFIX, name])
        res = os.environ.get(name)
        if res:
            # Check env variable (Jenkins build).
            return res
        else:
            res = requests.get(
                'http://metadata.google.internal/computeMetadata/'
                'v1/instance/attributes/{}'.format(name),
                headers={'Metadata-Flavor': 'Google'}
            )
            if res.status_code == 200:
                return res.text
    except requests.exceptions.ConnectionError:
        return default
    return default


class DefaultConfig(object):
    # PostgreSQL configurations.
    POSTGRESQL_DATABASE_USER = get_env_var('DB_USER', 'airtickets')
    POSTGRESQL_DATABASE_PASSWORD = get_env_var('DB_PASSWORD', 'airtickets')
    POSTGRESQL_DATABASE_DB = get_env_var('DB_NAME', 'airtickets')
    POSTGRESQL_DATABASE_HOST = get_env_var('DB_HOST', '127.0.0.1')

    SQLALCHEMY_DATABASE_URI = 'postgres://' + POSTGRESQL_DATABASE_USER + ':' \
                              + POSTGRESQL_DATABASE_PASSWORD + '@' \
                              + POSTGRESQL_DATABASE_HOST + '/' \
                              + POSTGRESQL_DATABASE_DB

    NEO4J_DATABASE_USER = get_env_var('NEO4J_USER', 'airtickets')
    NEO4J_DATABASE_PASSWORD = get_env_var(
        'NEO4J_PASSWORD', '<airtickets_pass>'
    )
    NEO4J_DATABASE_HOST = get_env_var('NEO4J_HOST', '127.0.0.1')
    config.DATABASE_URL = "bolt://{}:{}@{}:7687".format(
        NEO4J_DATABASE_USER, NEO4J_DATABASE_PASSWORD, NEO4J_DATABASE_HOST
    )
    config.ENCRYPTED_CONNECTION = False
    REDIS_URL = "redis://:@localhost:6379/5"

    # Determines the destination of the build.
    # Only usefull if you're using Frozen-Flask.
    FREEZER_DESTINATION = os.path.dirname(os.path.abspath(__file__)) + \
        '/../build'

    # the toolbar is only enabled in debug mode:
    DEBUG = False

    ELASTICSEARCH_HOST = "localhost:9200"

    # set a 'SECRET_KEY' to enable the Flask session cookies
    SECRET_KEY = 'A0Zr98j/3yX I~XHH!jmN]LWX/,?RT'

    SQLALCHEMY_TRACK_MODIFICATIONS = True

    FLIGHTSTATS_URL = 'https://api.flightstats.com'
    FLIGHTSTATS_APPID = 'f62cb23f'
    FLIGHTSTATS_APPKEY = '0d529248e16f6be628602b8a47315883'
