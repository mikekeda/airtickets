#!/usr/bin/env python

"""
    This script provides some easy to use commands.
"""

import csv
import sys
import os
import requests
import json

from flask import current_app
from flask_script import (Manager, Shell, Server, prompt, prompt_pass,
                          prompt_bool)
from flask_migrate import upgrade
from flask.ext.migrate import Migrate, MigrateCommand

from app import *
from extensions import db, es
from sqlalchemy.orm import joinedload
from elasticsearch import helpers


current_dir = os.path.dirname(os.path.realpath(__file__))

headers = {'content-type': 'application/json'}

manager = Manager(app)
migrate = Migrate(app, db)

# Run local server
manager.add_command("runserver", Server("localhost", port=5000))

manager.add_command('db', MigrateCommand)


@manager.command
def import_cities(file_name='csv_data/worldcities.csv'):
    if file_name[0] != '/':
        file_name = current_dir + '/' + file_name

    with open(file_name, 'rb') as csvfile:
        spamreader = csv.DictReader(csvfile)
        for idx, row in enumerate(spamreader):

            # create LanguageScript.
            lang = LanguageScript(row[' language script'])
            lang, created = lang.get_or_create(
                LanguageScript,
                language_script=lang.language_script
            )

            # create City.
            city = City(
                row[' GNS UFI'] or 0,
                row[' latitude'],
                row[' longitude'],
                row['ISO 3166-1 country code'],
                row[' FIPS 5-2 subdivision code'],
                row[' GNS FD'],
                row[' ISO 639-1 language code'],
            )
            if row[' GNS UFI']:
                city, created = city.get_or_create(City, gns_ufi=city.gns_ufi)
            else:
                city = city.save()

            # create CityName.
            name = CityName(
                row[' name'],
                lang.id,
                city.id
            )
            name, created = name.get_or_create(
                CityName,
                language_script_id=lang.id,
                city_id=city.id
            )

            print idx, row[' name']


@manager.command
def import_airports(file_name='csv_data/airports.csv'):
    if file_name[0] != '/':
        file_name = current_dir + '/' + file_name

    with open(file_name, 'rb') as csvfile:
        spamreader = csv.DictReader(csvfile)
        for idx, row in enumerate(spamreader):
            # create Airport.
            airport = Airport(
                row['Name'],
                row['City'],
                row['Country'],
                row['IATA/FAA'],
                row['ICAO'],
                row['Latitude'],
                row['Longitude'],
                row['Altitude'],
                row['Timezone'],
                row['DST'],
                row['Tz database time zone'],
            )
            airport.save()

            print idx, airport.name


@manager.command
def import_neo_airports(file_name='csv_data/airports.csv'):
    if file_name[0] != '/':
        file_name = current_dir + '/' + file_name

    url = app.config['NEO4J_URL'] + "/db/data/index/node/"
    payload = {
        "name": "geom",
        "config": {
            "provider": "spatial",
            "geometry_type": "point",
            "lat": "latitude",
            "lon": "longitude"
        }
    }
    requests.post(url, data=json.dumps(payload), headers=headers)

    with open(file_name, 'rb') as csvfile:
        spamreader = csv.DictReader(csvfile)
        for idx, row in enumerate(spamreader):
            # create Airport.
            airport = NeoAirport(
                airport_name=row['Name'],
                city=row['City'],
                country=row['Country'],
                iata_faa=row['IATA/FAA'],
                icao=row['ICAO'],
                latitude=row['Latitude'],
                longitude=row['Longitude'],
                altitude=row['Altitude'],
                timezone=row['Timezone'],
                dst=row['DST'],
                tz_database_time_zone=row['Tz database time zone'],
            )
            airport.save()

            # add node to geom index.
            airport_url = app.config['NEO4J_URL'] + "/db/data/node/" + str(airport._id)
            url = app.config['NEO4J_URL'] + "/db/data/index/node/geom"
            payload = {'value': 'dummy', 'key': 'dummy', 'uri': airport_url}
            requests.post(url, data=json.dumps(payload), headers=headers)

            # add node to Spatial index.
            # url = app.config['NEO4J_URL'] + "/db/data/ext/SpatialPlugin/graphdb/addNodeToLayer"
            # payload = {'layer': 'geom', 'node': airport_url}
            # requests.post(url, data=json.dumps(payload), headers=headers)

            print idx, airport.airport_name


@manager.command
def import_airlines(file_name='csv_data/airlines.csv'):
    if file_name[0] != '/':
        file_name = current_dir + '/' + file_name

    with open(file_name, 'rb') as csvfile:
        spamreader = csv.DictReader(csvfile)
        for idx, row in enumerate(spamreader):

            # create Airline.
            airline = Airline(
                row['Name'],
                row['Alias'],
                row['IATA'],
                row['ICAO'],
                row['Callsign'],
                row['Country'],
                row['Active'] == 'Y',
            )
            airline.save()

            try:
                print idx, airline.name
            except UnicodeEncodeError:
                print idx


@manager.command
def import_routes(file_name='csv_data/routes.csv'):
    if file_name[0] != '/':
        file_name = current_dir + '/' + file_name

    with open(file_name, 'rb') as csvfile:
        spamreader = csv.DictReader(csvfile)
        for idx, row in enumerate(spamreader):

            if not row['Source airport'] \
                or not row['Destination airport'] \
                or not row['Airline']:
                    continue

            airline = Airline.query.filter(Airline.iata == row['Airline']).first()
            source_airport = Airport.query.filter(Airport.iata_faa == row['Source airport']).first()
            destination_airport = Airport.query.filter(Airport.iata_faa == row['Destination airport']).first()

            if not airline \
                or not source_airport \
                or not destination_airport:
                    continue

            # create Route.
            route = Route(
                int(airline.id),
                int(source_airport.id),
                int(destination_airport.id),
                row['Codeshare'] == 'Y',
                row['Equipment'],
            )
            route.save()

            print idx, route.id, source_airport.name, '-', destination_airport.name


@manager.command
def import_neo_routes(file_name='csv_data/routes.csv'):
    """import routes."""
    if file_name[0] != '/':
        file_name = current_dir + '/' + file_name

    with open(file_name, 'rb') as csvfile:
        spamreader = csv.DictReader(csvfile)
        for idx, row in enumerate(spamreader):

            if not row['Source airport'] \
                or not row['Destination airport'] \
                    or not row['Airline']:
                print 'incorrect row'
                continue

            airline = Airline.query.filter(Airline.iata == row['Airline']).first()
            if not airline:
                print 'no airline', row['Airline']
                continue

            try:
                source_airport = NeoAirport.nodes.get(iata_faa=row['Source airport'])
            except NeoAirport.DoesNotExist:
                print 'no source_airport', row['Source airport']
                continue

            try:
                destination_airport = NeoAirport.nodes.get(iata_faa=row['Destination airport'])
            except NeoAirport.DoesNotExist:
                print 'no destination_airport', row['Destination airport']
                continue

            # create Route.
            route = source_airport.available_destinations.connect(destination_airport)
            route.airline = int(airline.id)
            route.distance = NeoAirport.get_distance(
                source_airport.latitude,
                source_airport.longitude,
                destination_airport.latitude,
                destination_airport.longitude,
            )
            route.codeshare = row['Codeshare'] == 'Y'
            route.equipment = row['Equipment']

            route.save()

            print idx, route._id, \
                source_airport.airport_name, '-', destination_airport.airport_name


@manager.command
def import_all():
    import_cities()
    import_airlines()
    import_neo_airports()
    import_neo_routes()



@manager.command
def create_cities_index():
    ITEMS_PER_PAGE = 1000

    index_body = {
        "settings": {
            "index" : {
                "analysis": {
                    "analyzer": {
                        "folding": {
                            "tokenizer": "standard",
                            "filter":  [ "lowercase", "asciifolding" ]
                        }
                    }
                }
            }
        },
        "mappings": {
            "CityName": {
                "properties": {
                    "value": {
                        "type": "string",
                        "index": "not_analyzed",
                        "fields": {
                            "folded": {
                                "type": "string",
                                "analyzer": "folding"
                            }
                        }
                    },
                    "data": {
                        "type": "nested"
                    }
                }
            }
        }
    }
    es.indices.create(index='main-index', body=index_body)

    num_of_items = CityName.query.count()
    num_of_pages = num_of_items // ITEMS_PER_PAGE + 1
    for page in range(num_of_pages):
        docs = []
        for city_name in CityName.query.options(joinedload(CityName.city)).offset(page * ITEMS_PER_PAGE).limit(ITEMS_PER_PAGE).all():
            docs.append(city_name.elastic_serialize())
        helpers.bulk(es, docs)
        print page, 'from', num_of_pages

@manager.command
def test():
    # jim = Person(name='Jim', age=3).save()
    # jim.age = 4
    # jim.save() # validation happens here
    # jim.delete()
    # jim.refresh() # reload properties from neo

    #add node to geom index
    # url = app.config['NEO4J_URL'] + "/db/data/ext/SpatialPlugin/graphdb/findGeometriesWithinDistance"
    # payload = {'layer': 'geom', 'pointY': 46.8625, 'pointX': -114.0117, 'distanceInKm': 175}
    # r = requests.post(url, data=json.dumps(payload), headers=headers)

    # print r.json()

    print NeoAirport.get_distance(-50, 5, 58, -30)


if __name__ == "__main__":
    manager.run()
