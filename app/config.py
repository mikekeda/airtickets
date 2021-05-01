import os
import requests

SITE_ENV_PREFIX = "AIRTICKETS"


def get_env_var(name: str, default: str = "") -> str:
    """Get all sensitive data from google vm custom metadata."""
    try:
        name = f"{SITE_ENV_PREFIX}_{name}"
        res = os.environ.get(name)
        if res:
            # Check env variable (Jenkins build).
            return res

        res = requests.get(
            "http://metadata.google.internal/computeMetadata/"
            "v1/instance/attributes/{}".format(name),
            headers={"Metadata-Flavor": "Google"},
        )
        if res.status_code == 200:
            return res.text
    except requests.exceptions.ConnectionError:
        return default
    return default


class DefaultConfig:
    # PostgreSQL configurations.
    SQLALCHEMY_DATABASE_URI = "postgresql://{}:{}@{}/{}".format(
        get_env_var("DB_USER", "airtickets"),
        get_env_var("DB_PASSWORD", "airtickets"),
        get_env_var("DB_HOST", "127.0.0.1"),
        get_env_var("DB_NAME", "airtickets"),
    )

    REDIS_URL = "redis://:@localhost:6379/5"

    # the toolbar is only enabled in debug mode:
    DEBUG = False

    ELASTICSEARCH_HOST = "localhost:9200"

    # Set a 'SECRET_KEY' to enable the Flask session cookies.
    SECRET_KEY = get_env_var("SECRET_KEY", "A0Zr98j/3yX I~XHH!jmN]LWX/,?RT")

    SQLALCHEMY_TRACK_MODIFICATIONS = True


class TestConfig(DefaultConfig):
    TESTING = True

    # PostgreSQL configurations.
    SQLALCHEMY_DATABASE_URI = "postgresql://{}:{}@{}/{}".format(
        get_env_var("TEST_DB_USER", "airtickets"),
        get_env_var("TEST_DB_PASSWORD", "airtickets"),
        get_env_var("DB_HOST", "127.0.0.1"),
        get_env_var("TEST_DB_NAME", "build_airtickets"),
    )

    REDIS_URL = "redis://:@localhost:6379/6"
