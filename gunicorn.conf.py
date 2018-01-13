"""Gunicorn config."""
# TODO: Doesn't work, need to check why.
# bind = 'unix:/uwsgi/airtickets.sock'
bind = '127.0.0.1:8001'
workers = 2
timeout = 30
max_requests = 100
daemon = False
# umask = '644'
user = 'nobody'
loglevel = 'info'
