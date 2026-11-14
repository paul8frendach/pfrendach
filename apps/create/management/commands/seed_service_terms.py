"""
Fill the plain-English agreement (terms) and FAQ on each Service.

Grounded in how OMV actually works — 50% books the date, high-quality delivery
within 30 days, one round of refinements, licensed music, FAA Part 107 flights,
owner-operated. Edit any of it later in the admin.

Only `terms` and `faq` are written, so existing summary/body/includes/process
copy is left exactly as Paul wrote it. Idempotent: matched by category.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

# Shared spine, then per-service specifics. Terms are "Title — detail"; FAQ is
# "Question :: Answer". Kept fair and plain — money and cancellation wording is
# deliberately light so Paul can tighten it in the admin.
_BOOKING = (
    "Booking — A 50% deposit books your date and holds it for you. It comes off "
    "the total, with the balance due before your final film is delivered."
)
_REVISIONS = (
    "Revisions — One round of refinements on the cut is included. Anything beyond "
    "that is quoted up front, never a surprise."
)
_DELIVERY = (
    "Delivery — Your finished, colour-graded film in high quality within 30 days, "
    "by secure download. Yours to keep, share and hold onto."
)
_MUSIC = (
    "Music — Scored to properly licensed music, cleared for you to post and share "
    "anywhere."
)
_COVERAGE = (
    "Where I work — Calvert, Anne Arundel and the surrounding counties as "
    "standard; anywhere further is a small travel add-on, agreed before we start."
)
_HANDS = (
    "One pair of hands — Owner-operated: Paul shoots every frame and cuts every "
    "film himself, so the person in the work is the person who turns up."
)

SERVICE_CONTENT = {
    "wedding": {
        "terms": [
            _BOOKING,
            "On the day — Eight hours of coverage as standard; extra hours and a "
            "second shooter can be added before the date.",
            _REVISIONS,
            _DELIVERY,
            _MUSIC,
            _HANDS,
        ],
        "faq": [
            "How far ahead should we book? :: Popular dates go six to twelve months out. The day is only held once your deposit is in.",
            "Do we get the raw footage? :: You get the finished film and the vertical social cuts. Raw files aren't part of the package, but can be arranged.",
            "Is it only you on the day? :: Yes, by design — one eye, start to finish. A second shooter can be added for larger weddings.",
            "What if it rains? :: We shoot rain or shine; only the drone work waits on weather, and that's rescheduled at no extra cost.",
        ],
    },
    "event": {
        "terms": [
            _BOOKING,
            "On the day — Coverage is booked by the hour; we agree the window and "
            "the must-have moments up front.",
            _REVISIONS,
            _DELIVERY,
            _MUSIC,
            _COVERAGE,
        ],
        "faq": [
            "How long do you cover? :: Whatever the event needs — coverage is booked by the hour and agreed before the day.",
            "How soon is the highlight ready? :: Within 30 days, with a quick-turn teaser available if you need something for the feed sooner.",
            "Can you work around a program? :: Yes — we map the must-have moments in advance so nothing is missed.",
        ],
    },
    "school": {
        "terms": [
            _BOOKING,
            "Season or one-off — Single games, a highlight tape, or a season "
            "package; recruiting tapes are built to share with coaches.",
            "Your footage too — Highlight and recruiting tapes can be cut from game "
            "film you already have.",
            _REVISIONS,
            _DELIVERY,
            _HANDS,
        ],
        "faq": [
            "Can you film a whole season? :: Yes — single games, a highlight tape, or a season package built to share with coaches.",
            "Do you edit footage I already have? :: Yes — recruiting and highlight tapes can be cut from your own game film.",
            "How are players identified? :: You tell me who to follow; the edit is built around the athletes that matter to you.",
        ],
    },
    "listing": {
        "terms": [
            _BOOKING,
            "Flights — Every aerial is flown under an FAA Part 107 licence, airspace "
            "and weather permitting; a weather day is rescheduled, never charged twice.",
            "Turnaround — Listing edits are built for speed, usually a few days, with "
            "a rush option when a date is tight.",
            _REVISIONS,
            _DELIVERY,
            _COVERAGE,
        ],
        "faq": [
            "Is the drone work licensed? :: Every flight is flown under an FAA Part 107 licence, with airspace and weather handled before the shoot.",
            "How fast is a listing turned around? :: Usually a few days — listing edits are built for speed, and a rush option is there when a date is tight.",
            "Do you shoot the interior too? :: Yes — ground and air in one visit, cut into a single film that moves.",
        ],
    },
    "brand": {
        "terms": [
            _BOOKING,
            "One film or a run — A single film, or a monthly batch of social reels; "
            "retainers are quoted to your posting cadence.",
            "Yours to use — Final films are licensed and cleared for your channels, "
            "ads and site.",
            _REVISIONS,
            _DELIVERY,
            _MUSIC,
        ],
        "faq": [
            "Do you do ongoing content? :: Yes — a single film or a monthly batch of social reels, quoted to your posting cadence.",
            "Who owns the final films? :: You do — licensed and cleared for your channels, ads and site.",
            "Can you match our brand? :: The look is built to your brand, not a template; we agree the direction up front.",
        ],
    },
}


class Command(BaseCommand):
    help = "Write the agreement (terms) and FAQ onto each live Service."

    def handle(self, *args, **opts):
        from apps.create.models import Service

        touched = missing = 0
        for category, content in SERVICE_CONTENT.items():
            svc = Service.objects.filter(category=category).first()
            if not svc:
                self.stderr.write(f"no Service for category {category!r}")
                missing += 1
                continue
            svc.terms = "\n".join(content["terms"])
            svc.faq = "\n".join(content["faq"])
            svc.save(update_fields=["terms", "faq"])
            touched += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Service terms + FAQ written: {touched} updated"
                + (f", {missing} missing" if missing else "")
            )
        )
