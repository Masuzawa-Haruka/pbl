"""
ASGI config for trading_text project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trading_text.settings")

application = get_asgi_application()
