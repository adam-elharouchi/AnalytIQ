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
forwarded_allow_ips = '*'  # trust X-Forwarded-* from Cloudflare/Render proxy


def post_fork(server, worker):
    """Reset inherited DB pool after fork — workers must not share connections."""
    try:
        from db import db_pool
        if db_pool is not None:
            db_pool.closeall()
        server.log.info("Worker %s: DB pool reset after fork", worker.pid)
    except Exception as e:
        server.log.warning("Worker %s: Could not reset DB pool: %s", worker.pid, e)


def worker_exit(server, worker):
    """Close all DB connections when a worker shuts down cleanly."""
    try:
        from db import db_pool
        if db_pool is not None:
            db_pool.closeall()
        server.log.info("Worker %s: DB pool closed on exit", worker.pid)
    except Exception as e:
        server.log.warning("Worker %s: Could not close DB pool: %s", worker.pid, e)


def worker_abort(server, worker):
    """Close DB connections on worker crash."""
    try:
        from db import db_pool
        if db_pool is not None:
            db_pool.closeall()
    except Exception:
        pass
