"""
Gunicorn config.
"""

bind = "unix:/uwsgi/airtickets.sock"
workers = 1
timeout = 30
max_requests = 100
daemon = False
umask = "91"
user = "www-data"
loglevel = "info"
