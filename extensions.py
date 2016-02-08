# -*- coding: utf-8 -*-
"""
    app.extensions
"""
from flask import Flask
from sqlalchemy import create_engine
from flask_sqlalchemy import SQLAlchemy
from flask.ext.cache import Cache
from flask.ext.redis import FlaskRedis
# from flask_migrate import Migrate

app = Flask(__name__)

# Database
app.config.from_object('app.config.DefaultConfig')
db = SQLAlchemy(app)
redis_store = FlaskRedis(app)
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], echo=False)
cache = Cache(app,config={'CACHE_TYPE': 'simple'})
