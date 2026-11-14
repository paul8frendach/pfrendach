"""
Seed the Create films console from the committed clips in static/omv/reel/.

Each Work row here points at a web clip and poster that ship with the site
(static/omv/reel/<name>), so the films console plays on the host with no media
server — the same arrangement the photo gallery uses.

Idempotent and non-destructive: rows are matched by slug and upserted, so
re-running only updates in place. A clip whose file is missing is skipped, and
rows already in the database that aren't listed here are left untouched.

Drafts (is_live False) are cut but held back from the public site until Paul
has confirmed them — ownership or consent still to check.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

# slug -> row. `clip`/`still` are filenames under static/omv/reel/.
REEL = [
    {
        "slug": "golden-hour",
        "title": "Golden hour",
        "category": "brand",
        "kind": "reel",
        "aspect": "tall",
        "clip": "autumn.mp4",
        "still": "autumn.jpg",
        "blurb": "An afternoon in the park, graded warm.",
        "year": "2025",
        "is_live": True,
        "is_featured": False,
        "sort": 10,
    },
    {
        "slug": "smart-home",
        "title": "Smart home tour",
        "category": "listing",
        "kind": "film",
        "aspect": "video",
        "clip": "listing.mp4",
        "still": "listing.jpg",
        "blurb": "A new build walked through, appliances and all.",
        "year": "2025",
        "is_live": True,
        "is_featured": False,
        "sort": 20,
    },
    # Held as drafts until Paul confirms — see the note from this session.
    # match: looks like a broadcast feed, not his own camera (US soccer only).
    # interesting: a candid of a stranger at an airport gate.
    {
        "slug": "match-film",
        "title": "Match film",
        "category": "school",
        "kind": "film",
        "aspect": "video",
        "clip": "match.mp4",
        "still": "match.jpg",
        "blurb": "Ninety minutes, cut to the moments that mattered.",
        "year": "2025",
        "is_live": False,
        "is_featured": False,
        "sort": 30,
    },
    {
        "slug": "interesting",
        "title": "Interesting",
        "category": "brand",
        "kind": "reel",
        "aspect": "tall",
        "clip": "airport.mp4",
        "still": "airport.jpg",
        "blurb": "A night at the gate.",
        "year": "2025",
        "is_live": False,
        "is_featured": False,
        "sort": 40,
    },
]


class Command(BaseCommand):
    help = "Upsert the films-console Work rows from static/omv/reel/."

    def handle(self, *args, **opts):
        from apps.create.models import Work

        reel_dir = Path(settings.BASE_DIR) / "static" / "omv" / "reel"
        made = updated = skipped = 0
        live = 0
        for row in REEL:
            for name in (row["clip"], row["still"]):
                if not (reel_dir / name).exists():
                    self.stderr.write(f"skip (file missing): {name}")
                    break
            else:
                defaults = {k: v for k, v in row.items() if k != "slug"}
                _, created = Work.objects.update_or_create(
                    slug=row["slug"], defaults=defaults
                )
                made += created
                updated += not created
                live += bool(row["is_live"])
                continue
            skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded reel: {made} new, {updated} updated, {live} live"
                + (f", {skipped} skipped" if skipped else "")
            )
        )
