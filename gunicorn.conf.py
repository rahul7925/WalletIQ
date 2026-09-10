import os

# Server socket
bind = "0.0.0.0:" + os.environ.get("PORT", "5000")

# Worker processes & threading
# On free-tier cloud containers (Render 512MB RAM, 0.1 CPU), running multiple heavy sync worker
# processes quickly causes memory exhaustion (OOM) and CPU throttling.
# Using 'gthread' (threaded workers) with preloading allows sharing memory and handling 8 concurrent
# requests with minimal memory footprint (~120-150MB total).
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "gthread")
workers = int(os.environ.get("WEB_CONCURRENCY", os.environ.get("GUNICORN_WORKERS", 2)))
threads = int(os.environ.get("GUNICORN_THREADS", 4))
preload_app = os.environ.get("GUNICORN_PRELOAD", "true").lower() in ("true", "1")

# Process lifecycle & memory leak prevention
# Periodically restarts workers after handling requests to keep memory tightly bounded
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", 1000))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", 50))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", 30))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", 5))

# Logging
accesslog = os.environ.get("GUNICORN_ACCESSLOG", "-")
errorlog = os.environ.get("GUNICORN_ERRORLOG", "-")
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info")
capture_output = True
enable_stdio_inheritance = True
