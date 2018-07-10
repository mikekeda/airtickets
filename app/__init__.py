import logging
from sqlalchemy import create_engine
from flask import Flask, url_for
from flask_debugtoolbar import DebugToolbarExtension
from flask_sqlalchemy import SQLAlchemy
from flask_redis import FlaskRedis
from flask_elasticsearch import FlaskElasticsearch

from app.config import get_env_var, DefaultConfig, TestConfig

app = Flask(__name__)
if get_env_var('TESTING', False):
    app.config.from_object(TestConfig)
else:
    app.config.from_object(DefaultConfig)
db = SQLAlchemy(app)
es = FlaskElasticsearch(app)
redis_store = FlaskRedis(app)
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], echo=False)

toolbar = DebugToolbarExtension(app)

# pylint: disable=E1101
app.jinja_env.globals['static'] = (
    lambda filename: url_for('static', filename=filename)
)

db.init_app(app)

# Disable elasticsearch warnings.
logger = logging.getLogger("elasticsearch")
logger.setLevel(logging.ERROR)

from app import views
