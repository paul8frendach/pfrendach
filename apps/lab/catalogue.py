"""Describing a coach's services once, and getting them into The LAB.

WHY THIS EXISTS
    A developer building a coach's website already knows what that coach sells —
    it is on the page they were hired to replace. The LAB knows it too, but only
    after somebody types it into Manage Services. When the two disagree, the
    website is the one that lies, because it is the one the parent reads.

    This module is the decoder between them: one declarative description of a
    service, checked against what The LAB actually needs, and rendered either as
    instructions a person can follow or as the payload a machine would post.

WHAT IT CANNOT DO, AND WHY
    **The LAB's public API has no write path for coach configuration.** Every
    POST it accepts creates a customer-side object — a lead, a booking, a
    review, a film order. Services, packages, durations, locations and
    availability are read-only over the API by design: `docs/FINDTHE90_INTEGRATION.md`
    §1a records the decision that configuration "flows outward from Manage
    Services" so that one answer feeds the coach's page, the API and every site
    built on it.

    So this does not create services. It produces the two things that are
    useful without that endpoint, and the one thing that would be needed with
    it:

      * `manual_brief()` — field-by-field instructions for Manage Services,
        in the order the form asks for them. Usable today.
      * `questions()`   — what to go back and ask the coach, when the developer
        has not been given enough to describe a service properly.
      * `lab_payload()` — the exact shape a `POST /api/v1/services` would take.
        Nothing consumes it yet. It exists so that the day that endpoint lands,
        the mapping has already been agreed and tested rather than invented in a
        hurry.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

# The LAB's own vocabulary. A spec that does not land on one of these values
# cannot be entered into Manage Services at all, so it is checked here rather
# than discovered by a coach staring at a dropdown.
SERVICE_TYPES = ("Training", "Game/Film Analysis", "Team Practice", "Other")
PRICING_MODES = ("fixed", "rate", "tiered")

# Severity, in the order a developer should act on them.
BLOCKS = "blocks"        # The service cannot be created at all.
DEGRADES = "degrades"    # It can, but it will not sell the way the coach expects.
POLISH = "polish"        # It will work; it just will not read as well.

_SEVERITY_ORDER = {BLOCKS: 0, DEGRADES: 1, POLISH: 2}


@dataclass(frozen=True)
class Gap:
    """Something missing, and the question that resolves it.

    `question` is written to be sent to a coach verbatim. A gap report that says
    "pricing_mode is required" makes the developer translate; one that says
    "Is this a flat price per session, an hourly rate, or does it change with
    session length?" can be forwarded without editing.
    """

    field: str
    severity: str
    what: str
    question: str

    @property
    def is_blocking(self) -> bool:
        return self.severity == BLOCKS


@dataclass
class ServiceSpec:
    """One service, as the website wants to offer it."""

    key: str                                  # stable id for reconciling
    title: str = ""
    type: str = ""
    sport: str = ""
    description: str = ""
    duration_minutes: int | None = None
    pricing_mode: str = ""
    is_per_athlete: bool | None = None
    # (athletes | None, price) for fixed/tiered; athletes None means flat rate.
    tiers: list[tuple[int | None, str]] = field(default_factory=list)
    hourly_rate: str | None = None            # rate mode
    durations: list[int] = field(default_factory=list)   # tiered mode, minutes
    price_floor: str | None = None
    locations: list[str] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "ServiceSpec":
        return cls(
            key=str(data.get("key") or data.get("title") or "").strip(),
            title=str(data.get("title") or "").strip(),
            type=str(data.get("type") or "").strip(),
            sport=str(data.get("sport") or "").strip(),
            description=str(data.get("description") or "").strip(),
            duration_minutes=data.get("duration_minutes"),
            pricing_mode=str(data.get("pricing_mode") or "").strip(),
            is_per_athlete=data.get("is_per_athlete"),
            tiers=[(t.get("athletes"), str(t.get("price")))
                   for t in (data.get("tiers") or []) if t.get("price") is not None],
            hourly_rate=(str(data["hourly_rate"]) if data.get("hourly_rate") is not None else None),
            durations=list(data.get("durations") or []),
            price_floor=(str(data["price_floor"]) if data.get("price_floor") is not None else None),
            locations=list(data.get("locations") or []),
            notes=str(data.get("notes") or "").strip(),
        )


def _money_ok(value) -> bool:
    try:
        return Decimal(str(value)) > 0
    except (InvalidOperation, TypeError, ValueError):
        return False


def questions(spec: ServiceSpec) -> list[Gap]:
    """Everything The LAB needs that this spec has not said.

    The order is deliberate: blocking gaps first, because a developer who reads
    three style notes before the one fact that stops the service existing has
    been given a checklist, not an answer.
    """
    gaps: list[Gap] = []

    def add(f, sev, what, question):
        gaps.append(Gap(field=f, severity=sev, what=what, question=question))

    if not spec.title:
        add("title", BLOCKS, "No name for the service.",
            "What should this be called on your page? A parent reads this "
            "before anything else.")

    if spec.type not in SERVICE_TYPES:
        add("type", BLOCKS,
            f"Type must be one of {', '.join(SERVICE_TYPES)}.",
            "Is this ordinary training, game or film analysis, a team practice, "
            "or something else? The LAB books each of those differently.")

    if not spec.sport:
        add("sport", BLOCKS, "No sport.",
            "Which sport is this for?")

    if not spec.duration_minutes:
        add("duration_minutes", BLOCKS, "No session length.",
            "How long is one session, in minutes? If it varies, give the usual "
            "length and the other options you offer.")

    if spec.pricing_mode not in PRICING_MODES:
        add("pricing_mode", BLOCKS, "No pricing mode.",
            "Is the price a flat amount per session, an hourly rate that scales "
            "with length, or does it change by session length and group size?")
    else:
        # Each mode needs different numbers, and the wrong ones are silently
        # ignored rather than rejected, so this is worth being strict about.
        if spec.pricing_mode == "rate":
            if not _money_ok(spec.hourly_rate):
                add("hourly_rate", BLOCKS, "Rate pricing with no hourly rate.",
                    "What is the hourly rate?")
        elif spec.pricing_mode in ("fixed", "tiered"):
            if not spec.tiers:
                add("tiers", BLOCKS,
                    f"{spec.pricing_mode.title()} pricing with no prices.",
                    "What does one session cost? If the price changes with the "
                    "number of players, give the price at each group size.")
            for athletes, price in spec.tiers:
                if not _money_ok(price):
                    add("tiers", BLOCKS, f"Price {price!r} is not a positive amount.",
                        f"What is the actual price for {athletes or 'a'} "
                        f"player{'' if athletes == 1 else 's'}?")
        if spec.pricing_mode == "tiered" and not spec.durations:
            add("durations", DEGRADES,
                "Tiered pricing with only one length, which is what fixed mode is for.",
                "Which session lengths do you offer for this, and what does each cost?")

    if spec.is_per_athlete is None:
        add("is_per_athlete", DEGRADES,
            "Not stated whether the price is per player or per session.",
            "Is that price per player, or for the whole session however many "
            "turn up? This is the single most misread number on a coaching page.")

    if not spec.locations:
        add("locations", DEGRADES,
            "No location, so The LAB will report this service as enquiry-only "
            "and no calendar can be drawn for it.",
            "Where does this happen? A named venue, or the areas you will "
            "travel to. Without one, the website can take an enquiry but "
            "cannot take a booking.")

    if not spec.description:
        add("description", POLISH, "No description.",
            "In a sentence, what does this session actually work on? This is "
            "what makes someone pick it over the one above it.")

    if spec.is_per_athlete and spec.pricing_mode in ("fixed", "tiered"):
        counts = [a for a, _ in spec.tiers if a]
        if counts and len(counts) == 1:
            add("tiers", POLISH,
                f"Per-player pricing quoted at {counts[0]} player(s) only.",
                "What is the largest group you will take for this, and does the "
                "per-player price change as the group grows?")

    gaps.sort(key=lambda g: _SEVERITY_ORDER[g.severity])
    return gaps


def is_complete(spec: ServiceSpec) -> bool:
    """True when nothing blocking is missing. Degraded is still creatable."""
    return not any(g.is_blocking for g in questions(spec))


def lab_payload(spec: ServiceSpec) -> dict:
    """The shape a write endpoint would take, mirroring The LAB's own models.

    Nothing consumes this yet — there is no `POST /api/v1/services`. It is
    written against `page.models.Service` / `ServiceDuration` / `Package` so
    that the mapping is agreed and tested before it is needed, rather than
    invented under time pressure on the day the endpoint appears.
    """
    payload: dict = {
        "title": spec.title,
        "type": spec.type,
        "sport": spec.sport,
        "description": spec.description,
        "duration_minutes": spec.duration_minutes,
        "pricing_mode": spec.pricing_mode,
        "is_per_athlete": bool(spec.is_per_athlete),
    }
    if spec.price_floor:
        payload["price_floor"] = spec.price_floor
    if spec.locations:
        payload["locations"] = spec.locations

    if spec.pricing_mode == "rate":
        # One Package carrying the hourly rate; The LAB multiplies by length
        # and then applies any floor.
        payload["packages"] = [{"athletes": 1 if spec.is_per_athlete else None,
                                "hourly_rate": spec.hourly_rate}]
    else:
        payload["durations"] = spec.durations or [spec.duration_minutes]
        payload["packages"] = [
            {"athletes": athletes, "price": price,
             "duration_minutes": (spec.durations[0] if spec.durations
                                  else spec.duration_minutes)}
            for athletes, price in spec.tiers
        ]
    return payload


def manual_brief(spec: ServiceSpec) -> list[str]:
    """Manage Services, field by field, in the order the form asks.

    This is the deliverable that works today: a person can follow it without
    knowing anything about the API, and it produces exactly the configuration
    the website is already built against.
    """
    lines = [
        f"Manage Services → Add a service",
        f"  Sport            : {spec.sport or '— ASK —'}",
        f"  Type             : {spec.type or '— ASK —'}",
        f"  Title            : {spec.title or '— ASK —'}",
        f"  Description      : {spec.description or '(leave blank)'}",
        f"  Session length   : {spec.duration_minutes or '— ASK —'} min",
        f"  Pricing mode     : {spec.pricing_mode or '— ASK —'}",
    ]
    if spec.pricing_mode == "rate":
        lines.append(f"  Hourly rate      : ${spec.hourly_rate or '— ASK —'}")
    else:
        if spec.durations:
            lines.append(f"  Lengths offered  : {', '.join(f'{d} min' for d in spec.durations)}")
        for athletes, price in spec.tiers:
            who = f"{athletes} player{'' if athletes == 1 else 's'}" if athletes else "flat rate"
            lines.append(f"  Price ({who:<12}): ${price}")
    if spec.price_floor:
        lines.append(f"  Price floor      : ${spec.price_floor}")
    lines.append(f"  Priced per player: {'yes' if spec.is_per_athlete else 'no'}")
    lines.append(f"  Locations        : {', '.join(spec.locations) if spec.locations else '— ASK — (no location = enquiry only)'}")
    if spec.notes:
        lines.append(f"  Note             : {spec.notes}")
    return lines


# ---------------------------------------------------------------- reconciling

@dataclass(frozen=True)
class Reconciliation:
    """What the website offers, against what the account actually holds."""

    matched: list[tuple[ServiceSpec, dict]] = field(default_factory=list)
    missing: list[ServiceSpec] = field(default_factory=list)      # declared, not in LAB
    unexpected: list[dict] = field(default_factory=list)          # in LAB, not declared
    drifted: list[tuple[ServiceSpec, dict, list[str]]] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return not (self.missing or self.unexpected or self.drifted)


def _norm(value: str) -> str:
    return " ".join(str(value or "").split()).casefold()


def reconcile(specs: list[ServiceSpec], live: list[dict]) -> Reconciliation:
    """Match on title, and report what differs.

    Title is the join key because it is the only field both sides are certain
    to have and a human chose. Ids cannot be used: The LAB allocates them, and
    a spec written before the service exists has none.
    """
    by_title = {_norm(s.get("title")): s for s in live}
    seen: set[str] = set()
    result = Reconciliation()

    for spec in specs:
        key = _norm(spec.title)
        found = by_title.get(key)
        if found is None:
            result.missing.append(spec)
            continue
        seen.add(key)
        differences = []

        want_minutes = spec.duration_minutes
        got_minutes = found.get("duration_minutes")
        if want_minutes and got_minutes and int(want_minutes) != int(got_minutes):
            differences.append(f"length: site says {want_minutes} min, LAB says {got_minutes} min")

        if spec.pricing_mode and found.get("pricing_mode") and \
                spec.pricing_mode != found.get("pricing_mode"):
            differences.append(f"pricing: site says {spec.pricing_mode}, "
                               f"LAB says {found['pricing_mode']}")

        price = found.get("price") or {}
        if spec.pricing_mode == "rate" and spec.hourly_rate and price.get("from_hourly"):
            if Decimal(spec.hourly_rate) != Decimal(price["from_hourly"]):
                differences.append(f"rate: site says ${spec.hourly_rate}/hr, "
                                   f"LAB says ${price['from_hourly']}/hr")
        elif spec.tiers and price.get("from"):
            cheapest = min(Decimal(p) for _, p in spec.tiers if _money_ok(p))
            if cheapest != Decimal(price["from"]):
                differences.append(f"price: site's cheapest is ${cheapest}, "
                                   f"LAB's is ${price['from']}")

        booking = (found.get("booking") or {}).get("mode")
        if booking == "enquiry" and spec.locations:
            differences.append("site expects bookable times, but LAB reports this "
                               "as enquiry-only (usually a missing location)")

        if differences:
            result.drifted.append((spec, found, differences))
        else:
            result.matched.append((spec, found))

    for title, found in by_title.items():
        if title not in seen:
            result.unexpected.append(found)
    return result


# ---------------------------------------------------------------- blocks

@dataclass
class BlockSpec:
    """A prepaid block, as the website wants to sell it.

    Kept apart from ServiceSpec because a block is not a service: it has no
    duration, no athlete tiers and no location of its own. It is N sessions OF
    a service, bought up front — which is why `service_key` points at one.

    Before The LAB grew SessionBlock, the only way to express this on a site was
    a service with no price and the word "block" in the description. That is how
    Six-Week Block came to sit in this file as a service that could not be
    created: the shape was wrong, not the data.
    """

    key: str
    title: str = ""
    service_key: str = ""
    sessions: int | None = None
    price: str | None = None
    valid_weeks: int | None = None
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "BlockSpec":
        return cls(
            key=str(data.get("key") or data.get("title") or "").strip(),
            title=str(data.get("title") or "").strip(),
            service_key=str(data.get("service_key") or "").strip(),
            sessions=data.get("sessions"),
            price=(str(data["price"]) if data.get("price") is not None else None),
            valid_weeks=data.get("valid_weeks"),
            description=str(data.get("description") or "").strip(),
        )


def block_questions(spec: BlockSpec, service_keys: list[str]) -> list[Gap]:
    gaps: list[Gap] = []

    def add(f, sev, what, question):
        gaps.append(Gap(field=f, severity=sev, what=what, question=question))

    if not spec.title:
        add("title", BLOCKS, "No name for the block.",
            "What should this block be called on your page?")

    if not spec.service_key:
        add("service_key", BLOCKS, "Not tied to a service.",
            "Which type of session do these count towards? A block is a number "
            "of sessions of one thing, not credit in general.")
    elif spec.service_key not in service_keys:
        add("service_key", BLOCKS,
            f"Points at '{spec.service_key}', which is not a service in this file.",
            "Which of your listed sessions does this block buy?")

    if not spec.sessions or spec.sessions < 2:
        add("sessions", BLOCKS, "No session count, or fewer than two.",
            "How many sessions does the block buy? Two or more — one session "
            "is just the session.")

    if not _money_ok(spec.price):
        add("price", BLOCKS, "No price for the block.",
            "What does the whole block cost?")

    if spec.valid_weeks is None:
        add("valid_weeks", DEGRADES,
            "No expiry window, so the sessions never lapse.",
            "How long do they have to use it? Leave it open if you would "
            "rather it never expired — but say so, because the website has to "
            "print one or the other.")

    if not spec.description:
        add("description", POLISH, "No description.",
            "In a sentence, what does the block get them?")

    gaps.sort(key=lambda g: _SEVERITY_ORDER[g.severity])
    return gaps


def block_manual_brief(spec: BlockSpec) -> list[str]:
    return [
        "Manage Services → the service → Blocks → Add a block",
        f"  Applies to       : {spec.service_key or '— ASK —'}",
        f"  Title            : {spec.title or '— ASK —'}",
        f"  Description      : {spec.description or '(leave blank)'}",
        f"  Sessions         : {spec.sessions or '— ASK —'}",
        f"  Price            : ${spec.price or '— ASK —'}",
        f"  Use within       : {f'{spec.valid_weeks} weeks' if spec.valid_weeks else 'no expiry'}",
    ]


def reconcile_blocks(specs: list[BlockSpec], live: list[dict]) -> Reconciliation:
    """Same shape as `reconcile`, matching on title."""
    by_title = {_norm(b.get("title")): b for b in live}
    seen: set[str] = set()
    result = Reconciliation()

    for spec in specs:
        found = by_title.get(_norm(spec.title))
        if found is None:
            result.missing.append(spec)
            continue
        seen.add(_norm(spec.title))
        differences = []
        if spec.sessions and found.get("sessions") and int(spec.sessions) != int(found["sessions"]):
            differences.append(f"sessions: site says {spec.sessions}, "
                               f"LAB says {found['sessions']}")
        if spec.price and found.get("price") and Decimal(spec.price) != Decimal(found["price"]):
            differences.append(f"price: site says ${spec.price}, LAB says ${found['price']}")
        # None on either side means "never expires", which is a real answer and
        # must not be compared as if it were zero.
        if spec.valid_weeks != found.get("valid_weeks"):
            differences.append(
                f"window: site says {spec.valid_weeks or 'no expiry'}, "
                f"LAB says {found.get('valid_weeks') or 'no expiry'}")
        (result.drifted if differences else result.matched).append(
            (spec, found, differences) if differences else (spec, found))

    for title, found in by_title.items():
        if title not in seen:
            result.unexpected.append(found)
    return result


def block_payload(spec: BlockSpec) -> dict:
    """The shape `POST /api/v1/blocks/write` takes."""
    return {
        "external_ref": spec.key,
        "service_external_ref": spec.service_key,
        "title": spec.title,
        "description": spec.description,
        "sessions": spec.sessions,
        "price": spec.price,
        "valid_weeks": spec.valid_weeks,
    }
