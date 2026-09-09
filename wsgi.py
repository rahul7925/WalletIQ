"""
wsgi.py — WSGI production entry point for Railway, Docker, and Gunicorn
Usage:
    gunicorn --config gunicorn.conf.py wsgi:app
"""

from app import app

if __name__ == '__main__':
    app.run()
