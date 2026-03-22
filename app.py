"""
AnalytIQ — application entry point.

Gunicorn target:  gunicorn app:app
Local dev:        python3 app.py
Testing:          from app import create_app; app = create_app()

All setup logic lives in core/factory.py. This file only:
  1. Defines create_app() — the canonical application factory.
  2. Instantiates app at module level for Gunicorn / import compatibility.
  3. Runs the dev server when invoked directly.
"""

import logging
import os
import sys

from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()

from flask import Flask  # noqa: E402 — after load_dotenv
from core.database import close_db_connection  # noqa: E402
from core import factory  # noqa: E402


def create_app() -> Flask:
    """
    Application factory.

    Returns a fully configured Flask app. Call this in tests with
    TESTING=True to get an isolated instance:

        app = create_app()
        app.config["TESTING"] = True
        client = app.test_client()
    """
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    factory.setup_logging(app)
    factory.configure_app(app)
    factory.setup_sentry(app)
    factory.setup_rate_limiting(app)
    factory.setup_csrf(app)
    factory.setup_swagger(app)
    factory.setup_celery(app)
    factory.register_request_hooks(app)
    factory.register_error_handlers(app)
    factory.register_blueprints(app)
    factory.register_frontend_routes(app)
    factory.run_migrations(app)

    app.teardown_appcontext(close_db_connection)

    with app.app_context():
        factory.register_api_versioning(app)

    return app


# Module-level instance — required by Gunicorn and any code that does
# `from app import app`.
app = create_app()


if __name__ == "__main__":
    import logging  # noqa: F811 — re-imported so test exec() namespaces have it
    import os  # noqa: F811
    import sys  # noqa: F811

    _logger = logging.getLogger("analytiq")

    port = int(os.getenv("PORT", 5001))
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true" or (
        os.getenv("FLASK_ENV") == "development" and "localhost" in os.getenv("HOST", "")
    )

    _logger.info("Starting Flask server on port %s (debug=%s)", port, debug_mode)
    _logger.info("API base URL: http://localhost:%s/api", port)
    _logger.info("Health check: http://localhost:%s/api/health", port)

    host = "0.0.0.0" if os.getenv("FLASK_ENV") == "production" else "127.0.0.1"

    try:
        app.run(debug=debug_mode, port=port, host=host)
    except OSError as e:
        if "Address already in use" in str(e):
            _logger.error(
                "Port %s is already in use. Stop the other process or choose "
                "a different port: python3 app.py 5002",
                port,
            )
        else:
            raise
