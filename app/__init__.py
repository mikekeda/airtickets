from flask import Flask, url_for
from flask_debugtoolbar import DebugToolbarExtension

from extensions import db
from .models import (City, LanguageScript, CityName, Airport, Airline,
                     Route, NeoAirport, NeoRoute)

app = Flask(__name__)
app.config.from_object('app.config.DefaultConfig')

toolbar = DebugToolbarExtension(app)

app.jinja_env.globals['static'] = (
    lambda filename: url_for('static', filename=filename)
)

db.init_app(app)

from app import views, models
