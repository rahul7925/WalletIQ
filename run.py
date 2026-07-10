"""
WalletIQ Production Launcher
============================
Development:   python run.py
Production:    gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 run:app

Before first run:
  flask --app app db upgrade
"""
from app import app, db
import logging
import socket
import sys

logging.basicConfig(level=logging.INFO)

PORT = 5000
HOST = '127.0.0.1'


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


if __name__ == '__main__':
    if _port_in_use(HOST, PORT):
        print(f"ERROR: Port {PORT} is already in use.")
        print("Stop other WalletIQ servers first (Ctrl+C in their terminals), then retry.")
        print("On Windows, multiple stale 'py -3 run.py' processes can cause random 500 errors.")
        sys.exit(1)

    with app.app_context():
        # Production setup should use Flask-Migrate (Alembic) migrations.
        # Keep db.create_all() disabled to avoid bypassing migration history.
        print("WalletIQ v2.0 Ready (apply migrations: flask --app app db upgrade)")

        print(f"Open: http://{HOST}:{PORT}")
        print("Multi-user: YES | Session isolation: YES | Database: MySQL")
    app.run(host=HOST, port=PORT, debug=False, threaded=True)
