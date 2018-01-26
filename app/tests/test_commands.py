#!/usr/bin/env python
# -*- coding: utf-8 -*-

from app.models import City, LanguageScript, CityName, Airline
from app.tests import BaseTestCase
from manage import import_cities, import_airlines, import_populations


class AirticketsCommandsTest(BaseTestCase):
    """ Manage.py commands. """

    def test_commands_import_cities(self):
        import_cities(rows=10)
        city = City.query.filter_by(gns_ufi=10735690).first()
        assert city
        lang = LanguageScript.query.filter_by(language_script='latin').first()
        assert lang
        city_name = CityName.query.filter_by(
            name='Sharan',
            language_script_id=lang.id,
            city_id=city.id
        ).first()
        assert city_name

    def test_commands_import_airlines(self):
        import_airlines(rows=10)
        assert Airline.query.filter_by(name="3D Aviation").first()

    def test_commands_import_populations(self):
        # Prepare city, language script and city name.
        city = City(gns_ufi=-782066, latitude=24.466667, longitude=54.366667)
        city.save()
        lang = LanguageScript(language_script='latin')
        lang.save()
        CityName(language_script_id=lang.id, city_id=city.id,
                 name='Abu dhabi').save()

        import_populations(rows=10)
        assert City.query.filter_by(latitude=24.466667, longitude=54.366667,
                                    population=603687).first()
