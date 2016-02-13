# -*- coding: utf-8 -*-
import os


class DefaultConfig(object):
    # MySQL configurations.
    MYSQL_DATABASE_USER = 'airtickets'
    MYSQL_DATABASE_PASSWORD = 'airtickets'
    MYSQL_DATABASE_DB = 'airtickets'
    MYSQL_DATABASE_HOST = 'localhost'
    MYSQL_CHARSET = 'utf8'

    # PostgreSQL configurations.
    POSTGRESQL_DATABASE_USER = 'airtickets'
    POSTGRESQL_DATABASE_PASSWORD = 'airtickets'
    POSTGRESQL_DATABASE_DB = 'airtickets'
    POSTGRESQL_DATABASE_HOST = 'postgres'

    if 'DOCKER' in os.environ:
        POSTGRESQL_DATABASE_HOST = 'postgres'
    else:
        POSTGRESQL_DATABASE_HOST = 'localhost'

    DATABASE = 'postgres'

    if 'DATABASE_URL' in os.environ:
        SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
    else:
        if DATABASE == 'mysql':
            SQLALCHEMY_DATABASE_URI = 'mysql://' + MYSQL_DATABASE_USER + ':' + MYSQL_DATABASE_PASSWORD + '@' + MYSQL_DATABASE_HOST + '/' + MYSQL_DATABASE_DB + '?charset=' + MYSQL_CHARSET
        elif DATABASE == 'postgres':
            SQLALCHEMY_DATABASE_URI = 'postgres://' + POSTGRESQL_DATABASE_USER + ':' + POSTGRESQL_DATABASE_PASSWORD + '@' + POSTGRESQL_DATABASE_HOST + '/' + POSTGRESQL_DATABASE_DB

    if 'GRAPHSTORY_URL' in os.environ:
        NEO4J_URL = os.environ['GRAPHSTORY_URL']
    elif 'DOCKER' in os.environ:
        NEO4J_URL = "http://neo4j:7474"
    else:
        NEO4J_URL = "http://localhost:7474"

    if 'REDIS_URL' in os.environ:
        REDIS_URL = os.environ['REDIS_URL']
    elif 'DOCKER' in os.environ:
        REDIS_URL = "redis://:@redis:6379/0"
    else:
        REDIS_URL = "redis://:@localhost:6379/0"

    # Determines the destination of the build. Only usefull if you're using Frozen-Flask.
    FREEZER_DESTINATION = os.path.dirname(os.path.abspath(__file__)) + '/../build'

    # the toolbar is only enabled in debug mode:
    DEBUG = False

    # set a 'SECRET_KEY' to enable the Flask session cookies
    SECRET_KEY = 'A0Zr98j/3yX I~XHH!jmN]LWX/,?RT'

    SQLALCHEMY_TRACK_MODIFICATIONS = True
