from flask_testing import TestCase

from app import app, db, redis_store


class BaseTestCase(TestCase):
    def create_app(self):
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        redis_store.flushall()
