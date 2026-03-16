"""
AnalytIQ Database Module
Manages the PostgreSQL connection pool shared across the application.
Extracted from app.py as Phase 1 of Blueprint extraction.
"""

import os
import socket
import time
import logging
from urllib.parse import urlparse

import psycopg2
from psycopg2 import pool
from flask import g

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global pool instance
# ---------------------------------------------------------------------------

db_pool = None

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def get_db_params(database_url=None):
    """Parse DATABASE_URL and return connection parameters dictionary"""
    url_to_parse = database_url or os.getenv("DATABASE_URL")
    if not url_to_parse:
        raise Exception("DATABASE_URL environment variable is not set")

    # Clean up the database URL - remove invalid query parameters like pgbouncer
    clean_url = url_to_parse.split("?")[0]

    try:
        # Handle both postgresql:// and postgres:// schemes
        url = clean_url
        if not url.startswith(("postgresql://", "postgres://")):
            if "://" not in url:
                url = "postgresql://" + url
            else:
                raise ValueError(f"Unsupported connection string scheme: {url.split('://')[0]}")

        from urllib.parse import unquote

        parsed = urlparse(url)

        if not parsed.hostname:
            raise ValueError("Hostname is missing from connection string")

        username = unquote(parsed.username) if parsed.username else "postgres"
        password = unquote(parsed.password) if parsed.password else ""
        database = parsed.path[1:] if parsed.path and len(parsed.path) > 1 else "postgres"

        return {
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "database": database,
            "user": username,
            "password": password,
        }
    except Exception as e:
        logger.error("Error parsing connection string: %s", e)
        return None


# ---------------------------------------------------------------------------
# Pool initialisation
# ---------------------------------------------------------------------------


def init_db_pool():
    """Initialize the database connection pool with timeout settings"""
    global db_pool
    if db_pool is not None:
        return

    database_url = os.getenv("DATABASE_URL")

    try:
        # Try to use simple direct connection string first (works with Supabase Pooler)
        # Ensure sslmode and timeout settings are configured
        clean_url = database_url

        # Add connection parameters if not present
        params_to_add = []
        if "sslmode" not in clean_url:
            params_to_add.append("sslmode=require")
        if "connect_timeout" not in clean_url:
            params_to_add.append("connect_timeout=10")
        # Note: statement_timeout via options is not supported on Supabase Transaction
        # Mode pooler (port 6543) — omitted intentionally.

        if params_to_add:
            separator = "&" if "?" in clean_url else "?"
            clean_url = clean_url + separator + "&".join(params_to_add)

        logger.info(
            "Initializing connection pool",
            extra={
                "connection_timeout": f"{config.DB_CONNECTION_TIMEOUT}s",
                "statement_timeout": f"{config.DB_STATEMENT_TIMEOUT}s",
                "min_connections": config.DB_POOL_MIN_CONNECTIONS,
                "max_connections": config.DB_POOL_MAX_CONNECTIONS,
            },
        )

        # Initialize connection pool with configuration
        db_pool = pool.ThreadedConnectionPool(
            minconn=config.DB_POOL_MIN_CONNECTIONS,
            maxconn=config.DB_POOL_MAX_CONNECTIONS,
            dsn=clean_url,
        )

        # Test the connection pool with a simple query
        try:
            test_conn = db_pool.getconn()
            test_cursor = test_conn.cursor()
            test_cursor.execute("SELECT 1")
            test_cursor.close()
            db_pool.putconn(test_conn)
            logger.info("Database connection pool initialized and tested successfully")
        except Exception as test_error:
            logger.warning("Pool created but test query failed: %s", test_error)
            # Don't raise - pool might still work for actual queries

    except psycopg2.OperationalError as e:
        logger.error("Pool initialization failed with direct URL: %s", e)
        # Fallback to resolved params if needed (usually direct URL works for pools)
        try:
            params = get_db_params(database_url)
            if params:
                # Resolve IPv4 if needed
                hostname = params["host"]
                try:
                    addrinfo = socket.getaddrinfo(
                        hostname, None, socket.AF_INET, socket.SOCK_STREAM
                    )
                    if addrinfo:
                        params["host"] = addrinfo[0][4][0]
                except Exception:
                    pass

                logger.info("Retrying with explicit connection parameters...")
                db_pool = pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=5,
                    user=params["user"],
                    password=params["password"],
                    host=params["host"],
                    port=params["port"],
                    database=params["database"],
                    sslmode="require",
                    connect_timeout=10,
                )
                logger.info("Database connection pool initialized with explicit params")
        except Exception as e2:
            logger.critical("Critical error initializing pool: %s", e2)
            logger.critical("Please check DATABASE_URL environment variable")
            raise


# ---------------------------------------------------------------------------
# Per-request connection management
# ---------------------------------------------------------------------------


def get_db_connection():
    """Get a connection from the global pool with retry logic"""
    global db_pool

    # Store connection in Flask g object for request duration
    if "db_conn" not in g:
        if db_pool is None:
            init_db_pool()

        # Retry logic for getting connection
        max_retries = 3
        retry_delay = 1  # seconds

        for attempt in range(max_retries):
            try:
                g.db_conn = db_pool.getconn()
                # Test the connection with a simple query
                try:
                    cursor = g.db_conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.close()
                except Exception as test_error:
                    # Connection is stale, close it and retry
                    logger.warning(
                        "Connection test failed on attempt %d: %s", attempt + 1, test_error
                    )
                    try:
                        db_pool.putconn(g.db_conn, close=True)
                    except Exception:
                        pass
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    raise
                break  # Success!

            except Exception as e:
                logger.warning(
                    "Error getting connection from pool (attempt %d/%d): %s",
                    attempt + 1,
                    max_retries,
                    e,
                )
                if attempt < max_retries - 1:
                    # Wait before retrying
                    time.sleep(retry_delay)
                    # Try to reinitialize pool on last retry
                    if attempt == max_retries - 2:
                        logger.info("Reinitializing connection pool...")
                        db_pool = None
                        init_db_pool()
                else:
                    # All retries failed
                    raise Exception(
                        f"Failed to get database connection after {max_retries} attempts: {str(e)}"
                    )

    return g.db_conn


def close_conn_safely(conn):
    """No-op: Connection closing is handled by teardown_appcontext"""
    pass


def close_db_connection(exception=None):
    """Return connection to pool at the end of request (teardown_appcontext handler)"""
    db_conn = g.pop("db_conn", None)
    if db_conn is not None and db_pool is not None:
        try:
            db_pool.putconn(db_conn)
        except Exception as e:
            logger.error("Error returning connection to pool: %s", e)
