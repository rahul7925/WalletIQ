import multiprocessing
import os

# Server socket
bind = "0.0.0.0:" + os.environ.get("PORT", "5000")

# Worker processes
# In cloud container environments (Render, Railway, ECS, Fly.io), cpu_count() reports host cores,
# causing severe OOM kills if 30+ workers spawn on a 512MB-1GB container.
# Clamp safe default between 2 and 4, and allow override via WEB_CONCURRENCY / GUNICORN_WORKERS.
_detected_cores = multiprocessing.cpu_count()
_default_workers = min(4, max(2, _detected_cores))
workers = int(os.environ.get("WEB_CONCURRENCY", os.environ.get("GUNICORN_WORKERS", _default_workers)))
threads = int(os.environ.get("GUNICORN_THREADS", 2))

# Process lifecycle
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", 30))
keepalive = 5

# Logging
accesslog = os.environ.get("GUNICORN_ACCESSLOG", "-")
errorlog = os.environ.get("GUNICORN_ERRORLOG", "-")
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info")
capture_output = True
enable_stdio_inheritance = True
