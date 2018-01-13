"""Gunicorn config."""
bind = 'unix:/uwsgi/airtickets.sock'
workers = 2
timeout = 30
max_requests = 100
daemon = False
umask = 0644
user = 'nobody'
loglevel = 'info'
