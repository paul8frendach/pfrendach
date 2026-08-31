"""Chrome context. Every template gets the house config, the pills, and the room."""

from django.conf import settings

from .models import SiteConfig, World

_WORLD_NAMESPACES = {"create", "build", "train"}


def _current_world(request) -> str:
    match = getattr(request, "resolver_match", None)
    if match and match.namespace in _WORLD_NAMESPACES:
        return match.namespace
    return "house"


def house(request):
    return {
        "site": SiteConfig.load(),
        "worlds": World.objects.filter(is_live=True),
        "site_url": settings.SITE_URL,
        "current_world": _current_world(request),
    }
