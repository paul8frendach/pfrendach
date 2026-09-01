"""Template helpers for the house."""

from pathlib import Path

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()

_STAMPS: dict[str, str] = {}


@register.simple_tag
def asset(path: str) -> str:
    """
    Static URL with a cache-buster stamped from the file's mtime.

    `runserver` serves static through a handler that sits *outside* the
    middleware chain, so no-store headers cannot be added there, and it sends
    only Last-Modified — which lets browsers heuristically cache a stylesheet
    or script and serve it with no request at all. The result is the worst
    class of bug: correct code on disk, wrong page on screen.

    In production WhiteNoise hashes filenames, so this adds nothing.
    """
    url = static(path)
    if not settings.DEBUG:
        return url

    if path not in _STAMPS or True:  # always re-stat in dev; the file is changing
        found = finders.find(path)
        try:
            _STAMPS[path] = str(int(Path(found).stat().st_mtime)) if found else "0"
        except OSError:
            _STAMPS[path] = "0"

    return f"{url}?v={_STAMPS[path]}"
