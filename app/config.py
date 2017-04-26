# -*- coding: utf-8 -*-
import os


class DefaultConfig(object):
    # PostgreSQL configurations.
    POSTGRESQL_DATABASE_USER = 'airtickets_admin'
    POSTGRESQL_DATABASE_PASSWORD = '<airTicKets465Y>'
    POSTGRESQL_DATABASE_DB = 'airtickets'
    POSTGRESQL_DATABASE_HOST = 'localhost'

    SQLALCHEMY_DATABASE_URI = 'postgres://' + POSTGRESQL_DATABASE_USER + ':' + POSTGRESQL_DATABASE_PASSWORD + '@' + POSTGRESQL_DATABASE_HOST + '/' + POSTGRESQL_DATABASE_DB

    NEO4J_URL = "http://localhost:7474"
    REDIS_URL = "redis://:@localhost:6379/0"

    # Determines the destination of the build. Only usefull if you're using Frozen-Flask.
    FREEZER_DESTINATION = os.path.dirname(os.path.abspath(__file__)) + '/../build'

    # the toolbar is only enabled in debug mode:
    DEBUG = False

    ELASTICSEARCH_HOST = "localhost:9200"

    # set a 'SECRET_KEY' to enable the Flask session cookies
    SECRET_KEY = 'A0Zr98j/3yX I~XHH!jmN]LWX/,?RT'

    SQLALCHEMY_TRACK_MODIFICATIONS = True

    FLIGHTSTATS_URL = 'https://api.flightstats.com'
    FLIGHTSTATS_APPID = 'f62cb23f'
    FLIGHTSTATS_APPKEY = '0d529248e16f6be628602b8a47315883'
