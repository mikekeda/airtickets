"""Gunicorn config."""
bind = 'unix:/uwsgi/airtickets.sock'
workers = 1
timeout = 3600
max_requests = 100
