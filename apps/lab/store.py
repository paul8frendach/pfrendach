"""What the Train views actually call.

Everything here answers `(data, notice)`. `notice` is None when the answer came
from The LAB, and a short sentence when it did not — which the template prints
instead of guessing. The rule this enforces: **never show a price we are not
currently sure of.** A stale tariff is worse than an honest "ask directly",
because a parent who reads $85 and is then quoted $95 has been misled by us.
"""
from __future__ import annotations

import logging

from django.conf import settings

from .client import client
from .errors import LabAccountError, LabConfigError, LabError, LabUnavailable
from .presenters import block_cards, service_cards, slot_cards

logger = logging.getLogger(__name__)

_UNAVAILABLE = "Sessions are being updated. Ask directly and a time will be made."
_UNCONFIGURED = "Sessions are set by hand at the moment. Ask directly."


def _ttl() -> int:
    return int(getattr(settings, "LAB_CACHE_SECONDS", 120))


def _handle(exc: LabError, *, what: str) -> str:
    """Log at the level that matches whose problem it is, and return the notice."""
    if isinstance(exc, LabConfigError):
        # Ours. Loud, because an unwired site looks identical to a quiet one.
        logger.error("LAB not wired up while loading %s: %s", what, exc)
        return _UNCONFIGURED
    if isinstance(exc, LabAccountError):
        # The coach's. Also loud: nothing in this codebase can fix a lapsed
        # subscription, and somebody has to be told to go and renew it.
        logger.error("LAB account cannot serve %s: %s", what, exc)
        return _UNCONFIGURED
    if isinstance(exc, LabUnavailable):
        logger.warning("LAB unreachable while loading %s: %s", what, exc)
        return _UNAVAILABLE
    logger.warning("LAB refused %s: %s", what, exc)
    return _UNAVAILABLE


def storefront(*, fresh: bool = False) -> tuple[list, str | None]:
    """The coach's services, as cards.

    `fresh=True` bypasses the cache. Verification has to: reading back a value
    this process wrote a second ago proves nothing if the answer comes from the
    cache rather than from The LAB.
    """
    try:
        return service_cards(client().services(cache_for=0 if fresh else _ttl())), None
    except LabError as exc:
        return [], _handle(exc, what="services")


def find_service(service_id: int):
    """One card by LAB id, or (None, notice)."""
    cards, notice = storefront()
    for card in cards:
        if card.id == service_id:
            return card, notice
    return None, notice


def prepaid_blocks(*, fresh: bool = False) -> tuple[list, str | None]:
    """The coach's prepaid blocks, as cards. `fresh=True` bypasses the cache."""
    try:
        return block_cards(client().blocks(cache_for=0 if fresh else _ttl())), None
    except LabError as exc:
        return [], _handle(exc, what="blocks")


def next_open(limit: int = 6) -> tuple[list, str | None]:
    """The soonest real bookable times across the coach's services.

    Only services The LAB reports as `booking.mode == "calendar"` are asked:
    anything else has no location or no packages, and calling availability for
    it produces an error the visitor cannot act on.

    One request per bookable service, cached. A coach's service list is short.
    """
    cards, notice = storefront()
    if not cards:
        return [], notice

    api = client()
    out: list = []
    reached = False
    for card in cards:
        if card.is_enquiry or len(out) >= limit:
            continue
        try:
            payload = api.availability(card.id, cache_for=_ttl())
        except LabError as exc:
            logger.warning("availability unavailable for service %s: %s", card.id, exc)
            continue
        reached = True
        out.extend(slot_cards(payload, card, limit=limit - len(out)))

    if out:
        return out[:limit], None
    if not reached:
        # Either nothing is bookable online, or every call failed. Both mean
        # the same thing to a visitor: there is no time to take here.
        return [], notice
    return [], None


def intake_definition() -> tuple[dict | None, str | None]:
    """The coach's live intake configuration.

    A disabled form is not an error — the coach turned it off — but it is also
    not something to render, so it comes back as None with a notice.
    """
    try:
        definition = client().intake_form(cache_for=_ttl())
    except LabError as exc:
        return None, _handle(exc, what="intake form")
    if not definition.get("is_enabled", True):
        return None, "The enquiry form is closed just now. Ask directly."
    return definition, None


def submit_lead(payload: dict, *, idempotency_key: str | None = None) -> dict:
    """Send an enquiry. Raises; the view decides what the visitor sees.

    Deliberately not caught here: a failed write must not look like a success,
    and the view is the only place that still has what the visitor typed.
    """
    return client().create_lead(payload, idempotency_key=idempotency_key)
