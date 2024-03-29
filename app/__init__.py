import logging

from flask import Flask, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_redis import FlaskRedis
from sqlalchemy import create_engine

from app.config import get_env_var, DefaultConfig, TestConfig

app = Flask(__name__)
if get_env_var("TESTING", False):
    app.config.from_object(TestConfig)
else:
    app.config.from_object(DefaultConfig)

app.debug = bool(get_env_var("DEBUG", "True"))

db = SQLAlchemy(app)
es = None
redis_store = FlaskRedis(app)
engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"], echo=False)

try:
    from flask_debugtoolbar import DebugToolbarExtension

    toolbar = DebugToolbarExtension(app)
except ImportError:
    DebugToolbarExtension = None
    toolbar = None

# pylint: disable=E1101
app.jinja_env.globals["static"] = lambda filename: url_for("static", filename=filename)

# Disable elasticsearch warnings.
logger = logging.getLogger("elasticsearch")
logger.setLevel(logging.ERROR)

from app import views
