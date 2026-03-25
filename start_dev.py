#!/usr/bin/env python3
"""Dev server launcher — sets CWD explicitly before starting Flask."""
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)
sys.path.insert(0, PROJECT_DIR)

os.environ.setdefault("PORT", "5001")
os.environ.setdefault("FLASK_ENV", "development")

# Now run the app
exec(open(os.path.join(PROJECT_DIR, "app.py")).read())
