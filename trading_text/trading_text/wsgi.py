"""
WSGI config for trading_text project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trading_text.settings")

application = get_wsgi_application()
