import os
import requests

SITE_ENV_PREFIX = "AIRTICKETS"


def get_env_var(name: str, default: str = "") -> str:
    """Get sensitive data from env vars, Oracle Cloud IMDS, or Google Cloud metadata."""
    name = f"{SITE_ENV_PREFIX}_{name}"

    env_var = os.environ.get(name)
    if env_var is not None:
        return env_var

    # Try Oracle Cloud IMDS (only reachable on OCI instances)
    try:
        res = requests.get(
            f"http://169.254.169.254/opc/v2/instance/metadata/{name}",
            headers={"Authorization": "Bearer Oracle"},
            timeout=2,
        )
        if res.status_code == 200:
            return res.text.strip()
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        pass

    # Try Google Cloud metadata (only reachable on GCP instances)
    try:
        res = requests.get(
            f"http://metadata.google.internal/computeMetadata/v1/instance/attributes/{name}",
            headers={"Metadata-Flavor": "Google"},
            timeout=2,
        )
        if res.status_code == 200:
            return res.text.strip()
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        pass

    return default


class DefaultConfig:
    # PostgresSQL configurations.
    SQLALCHEMY_DATABASE_URI = (
        "postgresql://"
        f"{get_env_var('DB_USER', 'airtickets')}:{get_env_var('DB_PASSWORD', 'airtickets')}"
        f"@{get_env_var('DB_HOST', '127.0.0.1')}/{get_env_var('DB_NAME', 'airtickets')}"
    )

    REDIS_URL = "redis://:@localhost:6379/5"

    # the toolbar is only enabled in debug mode:
    DEBUG = False

    # Set a 'SECRET_KEY' to enable the Flask session cookies.
    SECRET_KEY = get_env_var("SECRET_KEY", "A0Zr98j/3yX I~XHH!jmN]LWX/,?RT")

    SQLALCHEMY_TRACK_MODIFICATIONS = True


class TestConfig(DefaultConfig):
    TESTING = True

    # PostgresSQL configurations.
    SQLALCHEMY_DATABASE_URI = (
        "postgresql://"
        f"{get_env_var('TEST_DB_USER', 'airtickets_admin')}:{get_env_var('TEST_DB_PASSWORD', 'airtickets')}"
        f"@{get_env_var('DB_HOST', '127.0.0.1')}/{get_env_var('TEST_DB_NAME', 'test_airtickets')}"
    )

    REDIS_URL = "redis://:@localhost:6379/6"
