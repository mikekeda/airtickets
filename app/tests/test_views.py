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
