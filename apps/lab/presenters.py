"""LAB payloads, in the shape this site's templates already speak.

The Train storefront was built against local `SessionType` rows. Rather than
rewrite the markup around a dict, a service arrives here and leaves with the
same attribute names the template was already using — so the brand kit, the
tariff rows and the price styling are untouched by where the data now comes
from.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from django.urls import reverse

# How a LAB service type reads on a Frendach card. The LAB's vocabulary is
# platform-wide; this is Paul's.
FORMAT_LABELS = {
    "Training": "Training",
    "Game/Film Analysis": "Film analysis",
    "Team Practice": "Team practice",
    "Other": "Session",
}


def _money(value: str | None) -> str | None:
    """'85.00' -> '$85'. Whole dollars lose the decimals; cents keep them."""
    if value in (None, ""):
        return None
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    return f"${amount:,.0f}" if amount == int(amount) else f"${amount:,.2f}"


@dataclass(frozen=True)
class ServiceCard:
    """One service, ready to render."""

    id: int
    name: str
    summary: str
    duration_minutes: int | None
    format_display: str
    price_label: str
    price_note: str
    booking_mode: str
    booking_reason: str
    max_athletes: int | None
    raw: dict = field(repr=False, default_factory=dict)

    @property
    def is_enquiry(self) -> bool:
        return self.booking_mode == "enquiry"

    @property
    def url(self) -> str:
        return reverse("train:service_detail", args=[self.id])


def service_card(service: dict) -> ServiceCard:
    """Build a card from one `GET /api/v1/services` row.

    The price is printed, never computed. `from`/`to` already mean "what one
    session costs at the cheapest and dearest combination this service allows",
    with the coach's price floor applied — arithmetic here would only produce a
    number their own checkout contradicts.
    """
    price = service.get("price") or {}
    low, high = _money(price.get("from")), _money(price.get("to"))

    if low and high:
        price_label = f"{low} – {high}"
    elif low:
        price_label = low
    else:
        price_label = "On request"

    # Say what the range means, rather than leaving a parent to guess whether
    # it scales with players or with minutes.
    note = ""
    if low and high and service.get("is_per_athlete"):
        note = "depending on how many players"
    elif price.get("floor"):
        note = f"minimum {_money(price['floor'])}"
    elif price.get("mode") == "rate" and price.get("from_hourly"):
        hourly = _money(price["from_hourly"])
        # A one-hour session at an hourly rate prints the same figure twice
        # ("$70 · $70 per hour"), which reads like a mistake. Say what the
        # number means instead of repeating it.
        note = "per hour" if hourly == low else f"{hourly} per hour"

    return ServiceCard(
        id=service.get("id"),
        name=service.get("title") or "Session",
        summary=service.get("description") or "",
        duration_minutes=service.get("duration_minutes"),
        format_display=FORMAT_LABELS.get(service.get("type", ""), service.get("type", "Session")),
        price_label=price_label,
        price_note=note,
        booking_mode=(service.get("booking") or {}).get("mode", "enquiry"),
        booking_reason=(service.get("booking") or {}).get("reason", ""),
        max_athletes=service.get("max_athletes"),
        raw=service,
    )


def service_cards(services: list[dict]) -> list[ServiceCard]:
    return [service_card(s) for s in services]


@dataclass(frozen=True)
class SlotCard:
    """One bookable time, ready to render.

    The LAB returns the coach's LOCAL time with its offset attached and names
    the zone separately, so the wall-clock time is already correct. Parsing it
    and re-formatting in the server's zone is how a 6pm session in Swarthmore
    becomes a 10pm session on a website.
    """

    service_id: int
    service_name: str
    starts_at: str          # ISO 8601 with offset, as The LAB sent it
    day_label: str          # "Thursday 3 September"
    time_label: str         # "6:00 PM"
    location: str
    timezone: str

    @property
    def url(self) -> str:
        # Booking is not on this site yet, so a time leads to an enquiry that
        # already names it. Better than a button that cannot finish.
        return f"{reverse('train:enquire')}?service={self.service_id}&when={self.starts_at}"


_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December")
_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def _day_label(iso_date: str) -> str:
    """'2026-09-03' -> 'Thursday 3 September', without touching timezones."""
    try:
        year, month, day = (int(part) for part in iso_date.split("-"))
        weekday = date(year, month, day).weekday()
    except (ValueError, TypeError):
        return iso_date
    return f"{_DAYS[weekday]} {day} {_MONTHS[month - 1]}"


def slot_cards(availability: dict, service: "ServiceCard", limit: int = 6) -> list[SlotCard]:
    """Flatten one availability payload into cards, soonest first."""
    location = (availability.get("location") or {}).get("name", "")
    timezone = availability.get("timezone", "")
    out: list[SlotCard] = []
    for day in availability.get("days") or []:
        for slot in day.get("slots") or []:
            if len(out) >= limit:
                return out
            out.append(SlotCard(
                service_id=service.id,
                service_name=service.name,
                starts_at=slot.get("start", ""),
                day_label=_day_label(day.get("date", "")),
                time_label=slot.get("display_time", ""),
                location=location,
                timezone=timezone,
            ))
    return out


@dataclass(frozen=True)
class BlockCard:
    """A prepaid block, ready to render."""

    id: int
    title: str
    summary: str
    service_id: int
    service_name: str
    sessions: int
    price_label: str
    per_session_label: str
    saving_label: str
    window_label: str
    raw: dict = field(repr=False, default_factory=dict)

    @property
    def url(self) -> str:
        # Buying is not built on either side yet, so a block leads to an
        # enquiry that already names it. Better than a checkout that stops.
        return f"{reverse('train:enquire')}?block={self.id}"


def block_card(block: dict) -> BlockCard:
    saving = block.get("saving") or {}
    saving_label = ""
    if saving.get("percent") and saving.get("amount"):
        saving_label = f"save {_money(saving['amount'])} ({saving['percent']}%)"

    weeks = block.get("valid_weeks")
    # null means never, not zero. Printing "use within 0 weeks" from a null is
    # the obvious way to get this wrong.
    window_label = f"use within {weeks} weeks" if weeks else "no expiry"

    service = block.get("service") or {}
    return BlockCard(
        id=block.get("id"),
        title=block.get("title") or "Block",
        summary=block.get("description") or "",
        service_id=service.get("id"),
        service_name=service.get("title") or "",
        sessions=block.get("sessions") or 0,
        price_label=_money(block.get("price")) or "On request",
        per_session_label=_money(block.get("price_per_session")) or "",
        saving_label=saving_label,
        window_label=window_label,
        raw=block,
    )


def block_cards(blocks: list[dict]) -> list[BlockCard]:
    return [block_card(b) for b in blocks]
