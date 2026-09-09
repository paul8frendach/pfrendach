"""
PythonAnywhere WSGI entry point for paulfrendach.com.

Copy the contents of this file into the WSGI configuration file that
PythonAnywhere creates for the web app (Web tab -> "WSGI configuration file"),
replacing everything already in it. It is kept in the repo so the deployed
entry point is reviewable and version-controlled rather than existing only in
a textarea on their website.

Three things this does that the default template does not:

1. **Loads `.env` before Django.** Settings read `os.environ` at import, so a
   `.env` loaded afterwards has no effect and the app silently runs on
   defaults - DEBUG on, the wrong ALLOWED_HOSTS, no LAB key.
2. **Fails loudly on a missing secret key** rather than starting with the
   insecure development default and serving real traffic with it.
3. **Refuses to start with DEBUG on.** A debug page here would print the LAB
   API key straight into the browser, because settings hold it.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path("/home/pfrendach8/paulfrendach")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

if os.environ.get("DJANGO_DEBUG", "").lower() in {"1", "true", "yes", "on"}:
    raise RuntimeError(
        "DJANGO_DEBUG is on in production. Set DJANGO_DEBUG=false in .env "
        "before serving - debug pages leak settings, SQL and stack traces, "
        "and this project's settings hold a live LAB API key."
    )

if not os.environ.get("DJANGO_SECRET_KEY"):
    raise RuntimeError(
        "DJANGO_SECRET_KEY is not set. Generate one with:\n"
        "  python -c \"import secrets; print(secrets.token_urlsafe(64))\""
    )

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
