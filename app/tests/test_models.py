#!/usr/bin/env python
# -*- coding: utf-8 -*-
import math

from app.models import _deg2rad, PointMixin
from app.tests import BaseTestCase


class AirticketsModelTest(BaseTestCase):
    def test_deg2rad(self):
        self.assertEqual(_deg2rad(180), math.pi)

    def test_PointMixin(self):
        dist = PointMixin.get_distance(50.433333, 30.516667, 52.25, 21)
        self.assertEqual(round(dist, 12), 690.616317346638)
