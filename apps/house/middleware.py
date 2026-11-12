"""
House middleware.

OMVApexMiddleware — when the site is reached on the Oasis Media Visions domain,
the root serves the Create room (the OMV film house) instead of the house home.
One codebase, one deploy; the OMV apex simply opens on its own front door while
keeping the ꟼFrendach house chrome. Every other path behaves normally, so
/create, /train, /about and the admin are all still reachable on that host.

The hosts are read from the OMV_HOSTS env var (comma-separated) so the domain
can change without a code edit; it defaults to the real OMV apex + www.
"""

from __future__ import annotations

import os

_DEFAULT = "oasismediavisions.com,www.oasismediavisions.com"
OMV_HOSTS = {
    h.strip().lower()
    for h in os.environ.get("OMV_HOSTS", _DEFAULT).split(",")
    if h.strip()
}


class OMVApexMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/" and request.method in ("GET", "HEAD"):
            host = request.get_host().split(":")[0].lower()
            if host in OMV_HOSTS:
                # Imported lazily: the create app is loaded, but keep the
                # middleware import side-effect-free at startup.
                from apps.create.views import index

                return index(request)
        return self.get_response(request)
