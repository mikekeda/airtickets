# -*- coding: utf-8 -*-
"""
    This script provides some easy to use commands.
"""
import csv
import os
import json
import requests

from flask_script import Manager, Server
from flask_migrate import Migrate, MigrateCommand
from sqlalchemy.orm import joinedload
from neomodel import db as neomodel_db
from elasticsearch import helpers

from app import app
from app.models import (City, LanguageScript, CityName, Airport, Airline,
                        Route, NeoAirport)
from extensions import db, es


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

    with open(file_name, 'r') as csvfile:
        spamreader = csv.DictReader(csvfile)
        for idx, row in enumerate(spamreader):

            # create LanguageScript.
            lang = LanguageScript(row[' language script'])
            lang, _ = lang.get_or_create(
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
                city, _ = city.get_or_create(City, gns_ufi=city.gns_ufi)
            else:
                city = city.save()

            # create CityName.
            name = CityName(
                row[' name'],
                lang.id,
                city.id
            )
            name.get_or_create(
                CityName,
                language_script_id=lang.id,
                city_id=city.id
            )

            print(idx, row[' name'])


@manager.command
def import_airports(file_name='csv_data/airports.csv'):
    if file_name[0] != '/':
        file_name = current_dir + '/' + file_name

    with open(file_name, 'r') as csvfile:
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

            print(idx, airport.name)


@manager.command
def import_neo_airports(file_name='csv_data/airports.csv'):
    if file_name[0] != '/':
        file_name = current_dir + '/' + file_name

    url = "http://{}:7474/db/data/ext/SpatialPlugin/" \
          "graphdb/addSimplePointLayer".format(
              app.config['NEO4J_DATABASE_HOST']
          )
    payload = {
        "layer": "geom",
        "lat": "latitude",
        "lon": "longitude"
    }
    requests.post(
        url,
        data=json.dumps(payload),
        headers=headers,
        auth=(
            app.config['NEO4J_DATABASE_USER'],
            app.config['NEO4J_DATABASE_PASSWORD']
        )
    )

    with open(file_name, 'r') as csvfile:
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

            print(idx, airport.airport_name)

        # Add node to geom index.
        query = "match (t:NeoAirport) with t call spatial.addNode('geom',t) " \
                "YIELD node return count(*)"
        neomodel_db.cypher_query(query)


@manager.command
def import_airlines(file_name='csv_data/airlines.csv'):
    if file_name[0] != '/':
        file_name = current_dir + '/' + file_name

    with open(file_name, 'r') as csvfile:
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
                print(idx, airline.name)
            except UnicodeEncodeError:
                print(idx)


@manager.command
def import_routes(file_name='csv_data/routes.csv'):
    if file_name[0] != '/':
        file_name = current_dir + '/' + file_name

    with open(file_name, 'r') as csvfile:
        spamreader = csv.DictReader(csvfile)
        for idx, row in enumerate(spamreader):

            if not all([row['Source airport'], row['Destination airport'],
                        row['Airline']]):
                continue

            airline = Airline.query.filter(
                Airline.iata == row['Airline']
            ).first()
            source_airport = Airport.query.filter(
                Airport.iata_faa == row['Source airport']
            ).first()
            destination_airport = Airport.query.filter(
                Airport.iata_faa == row['Destination airport']
            ).first()

            if not all([airline, source_airport, destination_airport]):
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

            print(idx, route.id, source_airport.name, '-',
                  destination_airport.name)


@manager.command
def import_neo_routes(file_name='csv_data/routes.csv'):
    """import routes."""
    if file_name[0] != '/':
        file_name = current_dir + '/' + file_name

    with open(file_name, 'r') as csvfile:
        spamreader = csv.DictReader(csvfile)
        for idx, row in enumerate(spamreader):

            if not all([row['Source airport'], row['Destination airport'],
                        row['Airline']]):
                print('incorrect row')
                continue

            airline = Airline.query.filter(
                Airline.iata == row['Airline']
            ).first()
            if not airline:
                print('no airline', row['Airline'])
                continue

            try:
                source_airport = NeoAirport.nodes.get(
                    iata_faa=row['Source airport']
                )
            except NeoAirport.DoesNotExist:
                print('no source_airport', row['Source airport'])
                continue

            try:
                destination_airport = NeoAirport.nodes.get(
                    iata_faa=row['Destination airport']
                )
            except NeoAirport.DoesNotExist:
                print('no destination_airport', row['Destination airport'])
                continue

            # create Route.
            route = source_airport.available_destinations.connect(
                destination_airport
            )
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

            print(idx, route.id, source_airport.airport_name, '-',
                  destination_airport.airport_name)


@manager.command
def import_all():
    import_cities()
    import_airlines()
    import_neo_airports()
    import_neo_routes()


@manager.command
def create_cities_index():
    items_per_page = 1000

    index_body = {
        "settings": {
            "index": {
                "analysis": {
                    "analyzer": {
                        "folding": {
                            "tokenizer": "standard",
                            "filter":  ["lowercase", "asciifolding"]
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
                    "location": {
                        "type": "geo_point"
                    },
                    "population": {
                        "type": "integer"
                    },
                    "data": {
                        "type": "nested"
                    }
                }
            }
        }
    }

    try:
        es.indices.delete(index="main-index")
    except Exception as e:
        print(e)
    es.indices.create(index='main-index', body=index_body)

    num_of_items = CityName.query.count()
    num_of_pages = num_of_items // items_per_page + 1
    for page in range(num_of_pages):
        docs = []
        for city_name in CityName.query.options(joinedload(CityName.city))\
                .offset(page * items_per_page)\
                .limit(items_per_page)\
                .all():
            docs.append(city_name.elastic_serialize())
        helpers.bulk(es, docs)
        print(page, 'from', num_of_pages)


@manager.command
def import_populations(file_name='csv_data/cities-populations.csv'):
    """import populations."""
    if file_name[0] != '/':
        file_name = current_dir + '/' + file_name

    with open(file_name, 'r') as csvfile:
        spamreader = csv.DictReader(csvfile)
        for idx, row in enumerate(spamreader):
            if row['Population']:
                cities = City.query.options()\
                    .filter(City.latitude == float(row['Latitude']))\
                    .filter(City.longitude == float(row['Longitude']))\
                    .all()

                for city in cities:
                    city_names = [c.name.lower() for c in city.city_names]
                    if row['City'].lower() in city_names:
                        city.population = int(row['Population'])
                        city.save()

                        print(idx, row['City'], row['Country'], 'population',
                              row['Population'])


@manager.command
def import_flightstats_airports(file_name='csv_data/flightstats_airports.csv'):
    """import airports from flightstats."""
    if file_name[0] != '/':
        file_name = current_dir + '/' + file_name

    url = app.config['FLIGHTSTATS_URL'] + '/flex/airports/rest/v1/json/active'
    params = {
        'appId': app.config['FLIGHTSTATS_APPID'],
        'appKey': app.config['FLIGHTSTATS_APPKEY']
    }
    res = requests.get(url, params=params)

    if res.status_code == 200:

        with open(file_name, 'w') as csvfile:
            spamwriter = csv.writer(csvfile)

            json_data = res.json()['airports']

            airports_headers = []

            for row in json_data:
                for key in row.keys():
                    if key not in airports_headers:
                        airports_headers.append(key)

            spamwriter.writerow(airports_headers)

            for idx, row in enumerate(json_data):
                item_values = []

                for key in airports_headers:
                    value = row.get(key, '')

                    item_values.append(value)

                spamwriter.writerow(item_values)

                print(idx, row['name'])

            csvfile.close()


@manager.command
def import_flightstats_airlines(file_name='csv_data/flightstats_airlines.csv'):
    """import airlines from flightstats."""
    if file_name[0] != '/':
        file_name = current_dir + '/' + file_name

    url = app.config['FLIGHTSTATS_URL'] + '/flex/airlines/rest/v1/json/active'
    params = {
        'appId': app.config['FLIGHTSTATS_APPID'],
        'appKey': app.config['FLIGHTSTATS_APPKEY']
    }
    res = requests.get(url, params=params)

    if res.status_code == 200:

        with open(file_name, 'w') as csvfile:
            spamwriter = csv.writer(csvfile)

            json_data = res.json()['airlines']

            airlines_headers = []

            for row in json_data:
                for key in row.keys():
                    if key not in airlines_headers:
                        airlines_headers.append(key)

            spamwriter.writerow(airlines_headers)

            for idx, row in enumerate(json_data):
                item_values = []

                for key in airlines_headers:
                    value = row.get(key, '')
                    item_values.append(value)

                spamwriter.writerow(item_values)

                print(idx, row['name'])

            csvfile.close()


if __name__ == "__main__":
    manager.run()
