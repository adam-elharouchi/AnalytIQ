# Gunicorn configuration file
import multiprocessing

# Timeout in seconds (5 minutes)
timeout = 300
keepalive = 5
workers = 4
bind = "0.0.0.0:10000"
worker_class = "sync"
max_requests = 1000
max_requests_jitter = 50
