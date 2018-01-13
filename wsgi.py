from app import app
import bjoern

if __name__ == "__main__":
    sock = bjoern.bind_and_listen('unix:/uwsgi/airtickets.sock')
    bjoern.server_run(sock, app)
