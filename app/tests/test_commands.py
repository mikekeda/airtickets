#!/usr/bin/env python
# -*- coding: utf-8 -*-

from app.models import City, LanguageScript, CityName, Airline
from app.tests import BaseTestCase
from manage import import_cities, import_airlines


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
