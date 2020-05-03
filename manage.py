# -*- coding: utf-8 -*-
"""
    This script provides some easy to use commands.
"""
import csv
import os

from flask_script import Manager, Server
from flask_migrate import Migrate, MigrateCommand
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from neomodel.contrib.spatial_properties import NeomodelPoint
from elasticsearch import helpers
from elasticsearch.exceptions import (
    NotFoundError, ConnectionError as ElasticConnectionError
)

from app import app, db, es, redis_store
from app.models import City, LanguageScript, CityName, Airline, NeoAirport, get_distance


current_dir = os.path.dirname(os.path.realpath(__file__))
chunk_size = 100
headers = {'content-type': 'application/json'}

manager = Manager(app)
migrate = Migrate(app, db)

# Run local server
manager.add_command("runserver", Server("localhost", port=5000))

manager.add_command('db', MigrateCommand)


@manager.command
def import_cities(file_name='csv_data/worldcities.csv', rows=None):
    """ Import cities. """
    if file_name[0] != '/':
        file_name = current_dir + '/' + file_name

    with open(file_name, 'r') as csvfile:
        spamreader = csv.DictReader(csvfile)
        for idx, row in enumerate(spamreader):
            if rows and idx + 1 > rows:
                # The rows limit was achieved - stop import.
                break

            # Create a LanguageScript.
            lang, _ = LanguageScript.get_or_create(
                language_script=row[' language script']
            )

            # Create a City.
            city, _ = City.get_or_create(
                gns_ufi=row[' GNS UFI'] or 0,
                defaults={
                    'latitude': row[' latitude'],
                    'longitude': row[' longitude'],
                    'country_code': row['ISO 3166-1 country code'],
                    'subdivision_code': row[' FIPS 5-2 subdivision code'],
                    'gns_fd': row[' GNS FD'],
                    'language_code': row[' ISO 639-1 language code'],
                }
            )

            # Create a CityName.
            CityName.get_or_create(
                language_script_id=lang.id,
                city_id=city.id,
                defaults={'name': row[' name']}
            )

            print(idx, row[' name'])


@manager.command
def import_populations(file_name='csv_data/cities-populations.csv', rows=None):
    """ Import populations. """
    if file_name[0] != '/':
        file_name = current_dir + '/' + file_name

    with open(file_name, 'r') as csvfile:
        spamreader = csv.DictReader(csvfile)
        for idx, row in enumerate(spamreader):
            if rows and idx + 1 > rows:
                # The rows limit was achieved - stop import.
                break

            if row['Population']:
                cities = City.query.options().filter(
                    func.abs(City.latitude - float(row['Latitude'])) < 0.0005
                ).filter(
                    func.abs(City.longitude - float(row['Longitude'])) < 0.0005
                ).all()

                for city in cities:
                    city_names = [c.name.lower() for c in city.city_names]
                    if row['City'].lower() in city_names:
                        city.population = int(row['Population'])
                        city.save()

                        print(idx, row['City'], row['Country'], 'population',
                              row['Population'])


@manager.command
def import_airlines(file_name='csv_data/airlines.csv', rows=None):
    airline = None
    if file_name[0] != '/':
        file_name = current_dir + '/' + file_name

    with open(file_name, 'r') as csvfile:
        spamreader = csv.DictReader(csvfile)
        for idx, row in enumerate(spamreader):
            if rows and idx + 1 > rows:
                # The rows limit was achieved - stop import.
                break

            # Create Airline.
            airline, _ = Airline.get_or_create(
                name=row['Name'],
                alias=row['Alias'],
                iata=row['IATA'],
                icao=row['ICAO'],
                callsign=row['Callsign'],
                country=row['Country'],
                active=row['Active'] == 'Y',
                commit=(idx % chunk_size == 0)
            )

            print(idx, airline.name)

        # Save last chunk.
        airline.save()


@manager.command
def import_neo_airports(file_name='csv_data/airports.csv'):
    if file_name[0] != '/':
        file_name = current_dir + '/' + file_name

    with open(file_name, 'r') as csvfile:
        csvreader = csv.DictReader(csvfile)
        for idx, row in enumerate(csvreader):
            # create Airport.
            airport = NeoAirport(
                airport_name=row['Name'],
                city=row['City'],
                country=row['Country'],
                iata_faa=row['IATA/FAA'],
                icao=row['ICAO'],
                location=NeomodelPoint(latitude=row['Latitude'], longitude=row['Longitude'], height=row['Altitude']),
                timezone=row['Timezone'],
                dst=row['DST'],
                tz_database_time_zone=row['Tz database time zone'],
            )
            airport.save()

            print(idx, airport.airport_name)


@manager.command
def import_neo_routes(file_name='csv_data/routes.csv'):
    """ Import routes. """
    if file_name[0] != '/':
        file_name = current_dir + '/' + file_name

    with open(file_name, 'r') as csvfile:
        csvreader = csv.DictReader(csvfile)
        for idx, row in enumerate(csvreader):

            if not all([row['Source airport'], row['Destination airport'], row['Airline']]):
                print('incorrect row')
                continue

            airline = Airline.query.filter(Airline.iata == row['Airline']).first()
            if not airline:
                print('no airline', row['Airline'])
                continue

            try:
                # pylint: disable=E1101
                source_airport = NeoAirport.nodes.get(iata_faa=row['Source airport'])
            except NeoAirport.DoesNotExist:
                print('no source_airport', row['Source airport'])
                continue

            try:
                # pylint: disable=E1101
                destination_airport = NeoAirport.nodes.get(iata_faa=row['Destination airport'])
            except NeoAirport.DoesNotExist:
                print('no destination_airport', row['Destination airport'])
                continue

            # Create Route.
            route = source_airport.available_destinations.connect(
                destination_airport
            )
            route.airline = int(airline.id)
            route.distance = get_distance(
                source_airport.location.latitude,
                source_airport.location.longitude,
                destination_airport.location.latitude,
                destination_airport.location.longitude,
            )
            route.codeshare = row['Codeshare'] == 'Y'
            route.equipment = row['Equipment']

            route.save()

            print(idx, route.id, source_airport.airport_name, '-',
                  destination_airport.airport_name)


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
                        "type": "text",
                        "analyzer": "folding"
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
        es.indices.delete(index="airtickets-city-index")
    except (ElasticConnectionError, NotFoundError, AttributeError):
        return
    es.indices.create(index='airtickets-city-index', body=index_body)

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
def import_all():
    import_cities()
    import_populations()
    import_airlines()
    import_neo_airports()
    import_neo_routes()


@manager.command
def cleanup_redis():
    redis_store.flushall()


if __name__ == "__main__":
    manager.run()
