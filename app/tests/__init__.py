from flask_testing import TestCase

from app import app


class BaseTestCase(TestCase):
    def create_app(self):
        return app

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass