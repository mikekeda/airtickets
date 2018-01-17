#!/usr/bin/env python
# -*- coding: utf-8 -*-

from app.tests import BaseTestCase


class TestOptionMarker(BaseTestCase):
    def test_home_page(self):
        response = self.client.get('/')
        self.assert200(response)
        self.assert_template_used('index.html')

    def test_technologies_page(self):
        response = self.client.get('/technologies')
        self.assert200(response)
        self.assert_template_used('technologies.html')

    def test_autocomplete_cities_page(self):
        response = self.client.get('/ajax/autocomplete/cities?query=q')
        self.assert200(response)

    def test_airports_page(self):
        response = self.client.get(
            '/ajax/airports?lat=49.0&lng=23.0&limit=5&find_closest_city=true'
        )
        self.assert200(response)

    def test_routes_page(self):
        response = self.client.get(
            '/ajax/routes?from_airport=38991&to_airport=38990'
        )
        self.assert200(response)

    def test_get_cities_page(self):
        response = self.client.get(
            '/ajax/get-cities?ne_lng=25.0&ne_lat=51.0&sw_lng=24.0&sw_lat=50.0'
        )
        self.assert200(response)
