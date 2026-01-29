"""
This script provides some easy to use commands.
"""

import csv
from collections import defaultdict
from functools import wraps
import os
from time import time
from typing import Dict, Tuple, Optional

import click
from sqlalchemy.orm import joinedload
from elasticsearch import helpers
from elasticsearch.exceptions import (
    NotFoundError,
    ConnectionError as ElasticConnectionError,
)

from app import app, db, es, redis_store
from app.models import City, CityName, Airline, Airport, Route, get_distance

current_dir = os.path.dirname(os.path.realpath(__file__))
chunk_size = 1000


def timeit(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        print(f"func:{f.__name__} args:[{args}, {kw}] took: {round(te - ts, 3)} sec")
        return result

    return wrap


@app.cli.command()
@click.option("--file-name", type=click.Path(), default="csv_data/worldcities.csv")
@click.option("--rows", type=click.INT, default=None)
@timeit
def import_cities(file_name: str, rows: Optional[int]) -> None:
    """Import cities."""
    city_cache: Dict[Tuple[float, float], Optional[int]] = {}
    populations_cache = defaultdict(list)
    _cityname_cache = defaultdict(list)

    if file_name[0] != "/":
        file_name = current_dir + "/" + file_name

    # Populate cityname_cache.
    print("Populate cityname_cache...")
    with open(file_name, "r", encoding="utf-8") as csvfile:
        for idx, row in enumerate(csv.DictReader(csvfile)):
            if rows and idx + 1 > rows:
                break  # the rows limit was achieved - stop import

            location = (float(row[" latitude"]), float(row[" longitude"]))
            _cityname_cache[location].append(row[" name"].lower())

        cityname_cache = defaultdict(list)
        for location, names in _cityname_cache.items():
            for name in names:
                cityname_cache[name].extend(
                    [{"name": n, "location": location} for n in names]
                )

    # Populate populations_cache.
    print("Populate populations_cache...")
    with open(
        current_dir + "/csv_data/cities-populations.csv", "r", encoding="utf-8"
    ) as csvfile:
        csvreader = csv.DictReader(csvfile)
        for idx, row in enumerate(csvreader):
            if rows and idx + 1 > rows:
                break  # the rows limit was achieved - stop import

            if row["Population"]:
                location = (float(row["Latitude"]), float(row["Longitude"]))
                for city in cityname_cache[row["City"].lower()]:
                    if (
                        abs(city["location"][0] - location[0]) < 0.03
                        and abs(city["location"][1] - location[1]) < 0.03
                    ):
                        populations_cache[city["name"]].append(
                            {
                                "latitude": float(row["Latitude"]),
                                "longitude": float(row["Longitude"]),
                                "country_code": row["Country"].upper(),
                                "population": int(row["Population"]),
                            }
                        )

    # Create a City.
    with open(file_name, "r", encoding="utf-8") as csvfile:
        basket = []
        for idx, row in enumerate(csv.DictReader(csvfile)):
            if rows and idx + 1 > rows:
                break  # the rows limit was achieved - stop import

            location = (float(row[" latitude"]), float(row[" longitude"]))
            if location not in city_cache:
                population = [
                    p["population"]
                    for p in populations_cache[row[" name"].lower()]
                    if all(
                        [
                            p["country_code"] == row["ISO 3166-1 country code"].upper(),
                            abs(p["latitude"] - location[0]) < 0.03,
                            abs(p["longitude"] - location[1]) < 0.03,
                        ]
                    )
                ]
                population = population[0] if population else 0

                basket.append(
                    City(
                        gns_ufi=row[" GNS UFI"] or 0,
                        latitude=location[0],
                        longitude=location[1],
                        country_code=row["ISO 3166-1 country code"],
                        subdivision_code=row[" FIPS 5-2 subdivision code"],
                        gns_fd=row[" GNS FD"],
                        language_code=row[" ISO 639-1 language code"],
                        population=population,
                    )
                )
                city_cache[location] = None  # avoid adding same cities to database
                if len(basket) >= chunk_size:
                    db.session.bulk_save_objects(
                        basket, return_defaults=True
                    )  # we need to return ids
                    db.session.commit()  # save chunk

                    city_cache.update(
                        {(c.latitude, c.longitude): c.id for c in basket}
                    )  # set cache

                    basket = []  # empty basket

                print(idx, row[" name"], "(create City)")

        db.session.bulk_save_objects(basket, return_defaults=True)
        db.session.commit()  # save last chunk
        city_cache.update(
            {(c.latitude, c.longitude): c.id for c in basket}
        )  # set cache

    # Create a CityName.
    with open(file_name, "r", encoding="utf-8") as csvfile:
        basket = []
        for idx, row in enumerate(csv.DictReader(csvfile)):
            if rows and idx + 1 > rows:
                break  # the rows limit was achieved - stop import

            location = (float(row[" latitude"]), float(row[" longitude"]))

            basket.append(
                CityName(
                    lang=row[" language script"],
                    city_id=city_cache[location],
                    name=row[" name"],
                )
            )
            if len(basket) >= chunk_size:
                db.session.bulk_save_objects(basket)
                db.session.commit()  # save chunk
                basket = []  # empty basket

            print(idx, row[" name"], "(create CityName)")

        db.session.bulk_save_objects(basket)
        db.session.commit()  # save last chunk


@app.cli.command()
@click.option("--file-name", type=click.Path(), default="csv_data/airlines.csv")
@click.option("--rows", type=click.INT, default=None)
@timeit
def import_airlines(file_name: str, rows: Optional[int]) -> None:
    if file_name[0] != "/":
        file_name = current_dir + "/" + file_name

    with open(file_name, "r", encoding="utf-8") as csvfile:
        csvreader = csv.DictReader(csvfile)
        for idx, row in enumerate(csvreader):
            if rows and idx + 1 > rows:
                # The rows limit was achieved - stop import.
                break

            # Create Airline.
            airline = Airline(
                name=row["Name"],
                alias=row["Alias"],
                iata=row["IATA"],
                icao=row["ICAO"],
                callsign=row["Callsign"],
                country=row["Country"],
                active=row["Active"] == "Y",
            ).save(idx % chunk_size == 0)

            print(idx, airline.name)

        db.session.commit()  # save last chunk


@app.cli.command()
@click.option("--file-name", type=click.Path(), default="csv_data/airports.csv")
@timeit
def import_airports(file_name: str) -> None:
    if file_name[0] != "/":
        file_name = current_dir + "/" + file_name

    with open(file_name, "r", encoding="utf-8") as csvfile:
        csvreader = csv.DictReader(csvfile)
        for idx, row in enumerate(csvreader):
            # Create Airline.
            airport = Airport(
                airport_name=row["Name"],
                city=row["City"],
                country=row["Country"],
                iata_faa=row["IATA/FAA"],
                icao=row["ICAO"],
                latitude=row["Latitude"],
                longitude=row["Longitude"],
                timezone=row["Timezone"],
                dst=row["DST"],
                tz_database_time_zone=row["Tz database time zone"],
            ).save(idx % chunk_size == 0)

            print(idx, airport.airport_name)

        db.session.commit()  # save last chunk


@app.cli.command()
@click.option("--file-name", type=click.Path(), default="csv_data/routes.csv")
@timeit
def import_routes(file_name: str) -> None:
    """Import routes."""
    airlines_cache = {}
    airports_cache = {}

    if file_name[0] != "/":
        file_name = current_dir + "/" + file_name

    with open(file_name, "r", encoding="utf-8") as csvfile:
        csvreader = csv.DictReader(csvfile)
        for idx, row in enumerate(csvreader):
            if not all(
                [row["Source airport"], row["Destination airport"], row["Airline"]]
            ):
                print("incorrect row")
                continue

            if row["Airline"] in airlines_cache:
                airline_id = airlines_cache[row["Airline"]]
            else:
                airline = Airline.query.filter(Airline.iata == row["Airline"]).first()
                airline_id = getattr(airline, "id", None)
                airlines_cache[row["Airline"]] = airline_id

            if not airline_id:
                print("no airline", row["Airline"])
                continue

            if row["Source airport"] in airports_cache:
                source_airport = airports_cache[row["Source airport"]]
            else:
                source_airport = Airport.query.filter(
                    Airport.iata_faa == row["Source airport"]
                ).first()
                airports_cache[row["Source airport"]] = source_airport

            if not source_airport:
                print("no source_airport", row["Source airport"])
                continue

            if row["Destination airport"] in airports_cache:
                destination_airport = airports_cache[row["Destination airport"]]
            else:
                destination_airport = Airport.query.filter(
                    Airport.iata_faa == row["Destination airport"]
                ).first()
                airports_cache[row["Destination airport"]] = destination_airport

            if not destination_airport:
                print("no destination_airport", row["Destination airport"])
                continue

            # Create Route.
            Route(
                source=source_airport.id,
                destination=destination_airport.id,
                airline=airline_id,
                distance=get_distance(
                    source_airport.latitude,
                    source_airport.longitude,
                    destination_airport.latitude,
                    destination_airport.longitude,
                ),
                codeshare=row["Codeshare"] == "Y",
                equipment=row["Equipment"],
            ).save(idx % chunk_size == 0)

            print(
                idx, source_airport.airport_name, "-", destination_airport.airport_name
            )

        db.session.commit()  # save last chunk


@app.cli.command()
def create_cities_index() -> None:
    items_per_page = 1000

    index_body = {
        "settings": {
            "index": {
                "analysis": {
                    "analyzer": {
                        "folding": {
                            "tokenizer": "standard",
                            "filter": ["lowercase", "asciifolding"],
                        }
                    }
                }
            }
        },
        "mappings": {
            "CityName": {
                "properties": {
                    "value": {"type": "text", "analyzer": "folding"},
                    "location": {"type": "geo_point"},
                    "population": {"type": "integer"},
                    "data": {"type": "nested"},
                }
            }
        },
    }

    try:
        es.indices.delete(index="airtickets-city-index")
    except (ElasticConnectionError, NotFoundError, AttributeError):
        return
    es.indices.create(index="airtickets-city-index", body=index_body)

    num_of_items = CityName.query.count()
    num_of_pages = num_of_items // items_per_page + 1
    for page in range(num_of_pages):
        docs = []
        for city_name in (
            CityName.query.options(joinedload(CityName.city))
            .offset(page * items_per_page)
            .limit(items_per_page)
            .all()
        ):
            docs.append(city_name.elastic_serialize())
        helpers.bulk(es, docs)
        print(page, "from", num_of_pages)


@app.cli.command()
@click.pass_context
def import_all(ctx: click.Context) -> None:
    ctx.invoke(import_cities)
    ctx.invoke(import_airlines)
    ctx.invoke(import_airports)
    ctx.invoke(import_routes)


@app.cli.command()
def cleanup_redis():
    redis_store.flushall()


if __name__ == "__main__":
    app.cli()
