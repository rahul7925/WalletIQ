import multiprocessing
import os

bind = "0.0.0.0:" + os.environ.get("PORT", "5000")
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2
timeout = 120
keepalive = 5
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"
capture_output = True
enable_stdio_inheritance = True
