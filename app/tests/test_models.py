import math

from manage import app, import_cities, import_airlines
from app.models import _deg2rad, City, CityName, Airline, get_distance
from app.tests import BaseTestCase


class AirticketsModelsTest(BaseTestCase):
    """Test models and manage.py commands."""

    def test_deg2rad(self):
        self.assertEqual(_deg2rad(180), math.pi)

    def test_get_distance(self):
        dist = get_distance(50.433333, 30.516667, 52.25, 21)
        self.assertEqual(round(dist, 12), 690.616317346638)

    def test_commands_import_cities(self):
        runner = app.test_cli_runner()
        result = runner.invoke(import_cities, ["--rows", "10"])
        assert result.exit_code == 0

        # Test City model.
        city = City.query.filter_by(gns_ufi=10735690).first()
        self.assertIsNotNone(city)

        # Test City get_closest_cities() method.
        closest_city = City.get_closest_cities(33, 68)[0]
        # Different version of postgres have different precision.
        self.assertAlmostEqual(closest_city.pop("distance"), 43.9950902428921)
        self.assertDictEqual(
            closest_city,
            {
                "id": 1,
                "country_code": "AF",
                "data": {"lat": 33.175678, "lng": 68.730449},
                "population": 0,
                "value": "شرن",
            },
        )
        # Test City serialize() method.
        self.assertDictEqual(
            city.serialize(),
            {
                "city_names": ["شرن", "Sharan"],
                "country_code": "AF",
                "gns_fd": "PPLA",
                "gns_ufi": 10735690,
                "id": 1,
                "language_code": "ps",
                "latitude": 33.175678,
                "longitude": 68.730449,
                "population": 0,
                "subdivision_code": "29",
            },
        )

        # Test CityName model.
        city_name = CityName.query.filter_by(
            name="Sharan", lang="latin", city_id=city.id
        ).first()
        assert city_name

        # Test CityName serialize() method.
        self.assertDictEqual(
            city_name.serialize(), {"name": "Sharan", "city_id": city.id}
        )
        # Test CityName autocomplete_serialize() method.
        expected = {
            "value": "Sharan",
            "data": {"id": 1, "lng": 68.730449, "lat": 33.175678, "country_code": "AF"},
        }
        self.assertDictEqual(city_name.autocomplete_serialize(), expected)
        # Test CityName elastic_serialize() method.
        expected.update(
            {"location": {"lat": 33.175678, "lon": 68.730449}, "population": 0}
        )
        self.assertDictEqual(
            city_name.elastic_serialize(),
            {
                "_index": "airtickets-city-index",
                "_type": "CityName",
                "_id": 1,
                "_source": expected,
            },
        )

    def test_commands_import_airlines(self):
        """Test Airline model and import_airlines command."""
        runner = app.test_cli_runner()
        result = runner.invoke(import_airlines, ["--rows", "10"])
        assert result.exit_code == 0

        airline = Airline.query.filter_by(name="3D Aviation").first()
        self.assertTrue(airline)

        # Test Airline serialize() method.
        serialized_airline = airline.serialize()
        # Check all fields except id.
        assert all(
            serialized_airline.get(key) == val
            for key, val in {
                "name": "3D Aviation",
                "alias": "\\N",
                "iata": "",
                "icao": "SEC",
                "callsign": "SECUREX",
                "country": "United States",
                "active": False,
            }.items()
        )
