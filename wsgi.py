from app import app
import bjoern

if __name__ == "__main__":
    bjoern.run(app, 'unix:/uwsgi/airtickets.sock')
