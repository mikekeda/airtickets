#!/usr/bin/env python
# -*- coding: utf-8 -*-

from app.tests import BaseTestCase


class AirticketsViewTest(BaseTestCase):
    def test_home_page(self):
        def test():
            response = self.client.get("/")
            self.assert200(response)
            self.assert_template_used("index.html")

        test()  # first run.
        test()  # second run, to check cached result.

    def test_technologies_page(self):
        def test():
            response = self.client.get("/technologies")
            self.assert200(response)
            self.assert_template_used("technologies.html")

        test()  # first run.
        test()  # second run, to check cached result.

    def test_autocomplete_cities_page(self):
        def test():
            response = self.client.get("/ajax/autocomplete/cities?query=q")
            self.assert200(response)

        test()  # first run.
        test()  # second run, to check cached result.

    def test_airports_page(self):
        def test():
            response = self.client.get(
                "/ajax/airports?lat=49.0&lng=23.0" "&limit=5&find_closest_city=true"
            )
            self.assert200(response)

            response = self.client.get("/ajax/airports?lat=49.0&lng=23.0" "&limit=7")
            self.assert200(response)

        test()  # first run.
        test()  # second run, to check cached result.

    def test_routes_page(self):
        def test():
            response = self.client.get(
                "/ajax/routes?from_airport=38991&to_airport=38990"
            )
            self.assert200(response)

        test()  # first run.
        test()  # second run, to check cached result.

    def test_get_cities_page(self):
        def test():
            response = self.client.get(
                "/ajax/get-cities?ne_lng=25.0" "&ne_lat=51.0&sw_lng=24.0&sw_lat=50.0"
            )
            self.assert200(response)

        test()  # first run.
        test()  # second run, to check cached result.

    def test_page_not_found_page(self):
        def test():
            response = self.client.get("/not-exists")
            self.assert404(response)
            self.assert_template_used("404.html")

        test()  # first run.
        test()  # second run, to check cached result.
