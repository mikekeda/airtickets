from app import app
import bjoern

if __name__ == "__main__":
    try:
        bjoern.run(app, 'unix:/uwsgi/airtickets.sock')
    except KeyboardInterrupt:
        pass
