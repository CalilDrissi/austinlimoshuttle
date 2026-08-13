"""
Phusion Passenger entry point for cPanel / CloudLinux Python app hosting.

InMotion's "Setup Python App" looks for this file at the application root and
imports `application` from it. Committed from Phase 0 so the hosting assumption
is exercised continuously rather than discovered at deploy time.

Locally this file is inert -- `manage.py runserver` never imports it.

Deployment notes (InMotion shared hosting):
  * The cPanel Python selector creates a virtualenv under ~/virtualenv/<app>/3.12
    and re-executes the interpreter itself, so no sys.path juggling is needed
    beyond adding this directory.
  * Set DJANGO_SETTINGS_MODULE and the rest of the environment in the cPanel
    app's "Environment variables" panel, or in a .env file that sits OUTSIDE
    public_html. Never put secrets in the web root.
  * After each deploy: `manage.py migrate` and `manage.py collectstatic`, then
    hit "Restart" in cPanel (or touch tmp/restart.txt).
"""

import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
