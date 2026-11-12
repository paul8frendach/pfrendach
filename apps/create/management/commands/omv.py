"""
Oasis Media Visions control surface — the seam between the site and Oasis.

Subcommands
-----------
  seed       Idempotently plant the real packages, methods and site contact
             details. Safe to re-run; it updates in place and never duplicates.
  sync       Upsert Work / Package rows from a JSON file, so Oasis (or Grok)
             can push portfolio updates without touching the admin.
  requests   Emit commission requests (the OMV enquiries) as JSON for Oasis to
             read into its queue. --open limits to still-open ones;
             --mark-notified flags them so Oasis never double-counts.
  stats      One-line JSON census of the room, for the Oasis brief.

Everything here is the single source of truth for what the public OMV page
offers, so Oasis and the site never drift.
"""

from __future__ import annotations

import json
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.create.models import Commission, Method, Package, Work

# --------------------------------------------------------------------- real data
# Owner, contact and handles come straight from the signed OMV contract. The
# public OMV identity lives in the Create templates, not the house SiteConfig —
# this command never overwrites house-wide chrome.

METHODS = [
    {
        "name": "Talk it through",
        "kicker": "01 · Pre",
        "blurb": "We walk the day before it happens — the places, the people who matter, the moments you can't afford to miss.",
        "detail": "A shot list that still leaves room for what you can't plan. The best frames are never on the schedule.",
        "gear": "Planning call, venue scout, shot list",
    },
    {
        "name": "Shoot it quiet",
        "kicker": "02 · Day-of",
        "blurb": "On the day I work discreetly, dressed for the room. One eye on the light, one on the moment.",
        "detail": "Cinema cameras and prime lenses. A drone in the air when the place earns it.",
        "gear": "Cinema camera, primes, gimbal, drone",
    },
    {
        "name": "Cut for feeling",
        "kicker": "03 · Edit",
        "blurb": "Color-graded, scored to licensed music, cut for emotion first and shareability second.",
        "detail": "A private preview link before anything is final, so the film is yours before the world sees it.",
        "gear": "Color grade, licensed score, private preview",
    },
    {
        "name": "Deliver it right",
        "kicker": "04 · Deliver",
        "blurb": "Your film in high quality within 30 days, plus the vertical cuts for the feed.",
        "detail": "Delivered by secure download. Yours to keep, share and hold onto forever.",
        "gear": "1080p+ MP4, vertical social edits, secure download",
    },
]

# "From" prices are honest anchors Paul can edit in the admin at any time.
# The wedding figure is the real floor from the OMV contract ($760 + $350).
PACKAGES = [
    {
        "name": "Wedding Film",
        "summary": "Eight hours of coverage and one cinematic highlight film of the whole day.",
        "deliverables": (
            "8 consecutive hours of day-of coverage\n"
            "One 6–10 minute cinematic highlight film\n"
            "Color grade and licensed music\n"
            "Delivered in 1080p+ within 30 days\n"
            "Vertical cut for the feed"
        ),
        "turnaround": "30 days",
        "price_from": "1110",
        "price_note": "50% books the date",
        "is_featured": True,
        "sort": 10,
    },
    {
        "name": "Listing Film & Drone",
        "summary": "A property that moves — ground and air — for agents who want the scroll to stop.",
        "deliverables": (
            "Cinematic walk-through of the home\n"
            "Licensed FAA Part 107 drone aerials\n"
            "Branded for your listing\n"
            "Wide cut for the MLS, vertical for the feed\n"
            "48–72 hour turnaround"
        ),
        "turnaround": "48–72 hours",
        "price_from": "350",
        "price_note": "Per listing",
        "is_featured": True,
        "sort": 20,
    },
    {
        "name": "School & Sports Film",
        "summary": "Senior nights, season films and highlight reels that look like the big stage.",
        "deliverables": (
            "Game-day or season coverage\n"
            "Highlight film cut to music\n"
            "Player and team edits\n"
            "Delivered in 1080p+\n"
            "Social cuts included"
        ),
        "turnaround": "2 weeks",
        "price_from": "500",
        "price_note": "On request",
        "is_featured": False,
        "sort": 30,
    },
    {
        "name": "Brand & Business Film",
        "summary": "Content for small businesses that refuses to look like content.",
        "deliverables": (
            "Half or full day of filming\n"
            "One brand film plus stills\n"
            "Cut wide for the site, vertical for the feed\n"
            "Every crop framed on purpose"
        ),
        "turnaround": "2–3 weeks",
        "price_from": "600",
        "price_note": "On request",
        "is_featured": False,
        "sort": 40,
    },
    {
        "name": "Event Highlight",
        "summary": "Parties, showers, reunions — the day, told in three minutes that feel like it.",
        "deliverables": (
            "Up to 4 hours of coverage\n"
            "One 2–4 minute highlight film\n"
            "Licensed music and color grade\n"
            "Delivered in 2 weeks"
        ),
        "turnaround": "2 weeks",
        "price_from": "450",
        "price_note": "On request",
        "is_featured": False,
        "sort": 50,
    },
    {
        "name": "Social Reels",
        "summary": "A standing drip of vertical content, shot and cut on a rhythm.",
        "deliverables": (
            "A shoot day of vertical content\n"
            "A set of edited reels\n"
            "Captions and licensed audio\n"
            "Sized for every feed"
        ),
        "turnaround": "Rolling",
        "price_from": "150",
        "price_note": "From / per shoot",
        "is_featured": False,
        "sort": 60,
    },
]

# Portfolio structure. Seeded as drafts (is_live=False) so nothing unverified
# goes public — Paul flips each live, or ingests real films from the drives,
# and the category grid fills itself.
WORK_DRAFTS = [
    {"title": "A Maryland Wedding", "category": "wedding", "kind": "film",
     "blurb": "Eight hours, one film, the whole day.", "aspect": "wide"},
    {"title": "Listing Reel", "category": "listing", "kind": "reel",
     "blurb": "Ground and air, cut for the scroll.", "aspect": "video"},
    {"title": "Season Film", "category": "school", "kind": "film",
     "blurb": "Senior night on the big stage.", "aspect": "wide"},
    {"title": "Brand Day", "category": "brand", "kind": "film",
     "blurb": "A small business on its best day.", "aspect": "video"},
]


class Command(BaseCommand):
    help = "Oasis Media Visions control surface: seed, sync, requests, stats."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["seed", "sync", "requests", "stats"])
        parser.add_argument("--file", help="JSON file for `sync`.")
        parser.add_argument("--open", action="store_true", help="`requests`: only still-open ones.")
        parser.add_argument("--json", action="store_true", help="Emit JSON.")
        parser.add_argument(
            "--mark-notified",
            action="store_true",
            help="`requests`: flag emitted rows so Oasis does not re-count them.",
        )

    def handle(self, *args, **opts):
        getattr(self, f"_do_{opts['action']}")(opts)

    # ---------------------------------------------------------------- seed

    def _do_seed(self, opts):
        for i, m in enumerate(METHODS):
            Method.objects.update_or_create(
                name=m["name"],
                defaults={**m, "sort": (i + 1) * 10, "is_live": True},
            )
        for p in PACKAGES:
            slug = slugify(p["name"])
            price = Decimal(p["price_from"]) if p["price_from"] else None
            # Deposit that books the date = half the floor, roundable in admin.
            deposit = price * Decimal("0.5") if price is not None else None
            if deposit is not None:
                deposit = deposit.quantize(Decimal("1"))
            Package.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": p["name"],
                    "summary": p["summary"],
                    "deliverables": p["deliverables"],
                    "turnaround": p["turnaround"],
                    "price_from": price,
                    "price_note": p["price_note"],
                    "deposit_amount": deposit,
                    "allow_online_booking": deposit is not None,
                    "is_featured": p["is_featured"],
                    "sort": p["sort"],
                    "is_live": True,
                },
            )
        for i, w in enumerate(WORK_DRAFTS):
            slug = slugify(w["title"])
            Work.objects.update_or_create(
                slug=slug,
                defaults={
                    "title": w["title"],
                    "category": w["category"],
                    "kind": w["kind"],
                    "blurb": w["blurb"],
                    "aspect": w["aspect"],
                    "credit": "Oasis Media Visions",
                    "is_featured": i == 0,
                    "is_live": False,  # drafts: nothing unverified goes public
                    "sort": (i + 1) * 10,
                },
            )
        # Authoritative: the OMV set is the Create room. Retire any older methods
        # or packages seeded before the rebrand so the page shows only these.
        canonical_methods = [m["name"] for m in METHODS]
        canonical_packages = [slugify(p["name"]) for p in PACKAGES]
        retired_m = Method.objects.filter(is_live=True).exclude(
            name__in=canonical_methods
        ).update(is_live=False)
        retired_p = Package.objects.filter(is_live=True).exclude(
            slug__in=canonical_packages
        ).update(is_live=False)
        if retired_m or retired_p:
            self.stdout.write(f"Retired {retired_m} stale method(s), {retired_p} stale package(s).")
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {Method.objects.count()} methods, {Package.objects.count()} packages, "
            f"{Work.objects.count()} work rows ({Work.objects.filter(is_live=False).count()} drafts). "
            "Flip work live in the admin, or ingest real films from the drives."
        ))

    # ---------------------------------------------------------------- sync

    def _do_sync(self, opts):
        if not opts.get("file"):
            raise CommandError("sync needs --file path/to/content.json")
        with open(opts["file"], encoding="utf-8") as fh:
            data = json.load(fh)
        n_work = n_pkg = 0
        for w in data.get("work", []):
            slug = w.get("slug") or slugify(w["title"])
            fields = {k: v for k, v in w.items() if k in {
                "title", "kind", "category", "year", "client", "location", "blurb",
                "description", "video_url", "instagram_url", "aspect", "runtime",
                "credit", "is_featured", "is_live", "sort",
            }}
            fields.setdefault("credit", "Oasis Media Visions")
            Work.objects.update_or_create(slug=slug, defaults=fields)
            n_work += 1
        for p in data.get("packages", []):
            slug = p.get("slug") or slugify(p["name"])
            fields = {k: v for k, v in p.items() if k in {
                "name", "summary", "deliverables", "turnaround", "price_from",
                "price_note", "is_featured", "is_live", "sort",
            }}
            Package.objects.update_or_create(slug=slug, defaults=fields)
            n_pkg += 1
        self.stdout.write(self.style.SUCCESS(f"Synced {n_work} work, {n_pkg} packages from {opts['file']}."))

    # ---------------------------------------------------------------- requests

    def _do_requests(self, opts):
        qs = Commission.objects.all()
        if opts["open"]:
            qs = qs.filter(status__in=[
                Commission.Status.NEW, Commission.Status.READ, Commission.Status.QUOTED
            ])
        rows = [{
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
            "service": c.service,
            "service_label": c.get_service_display(),
            "event_date": c.event_date.isoformat() if c.event_date else None,
            "location": c.location,
            "budget": c.budget,
            "status": c.status,
            "details": c.details,
            "created": c.created_at.isoformat(),
        } for c in qs]
        if opts["mark_notified"]:
            qs.update(notified_oasis=True)
        if opts["json"]:
            self.stdout.write(json.dumps(rows, indent=2))
        else:
            if not rows:
                self.stdout.write("No commission requests.")
            for r in rows:
                self.stdout.write(
                    f"#{r['id']} {r['service_label']} · {r['name']} · "
                    f"{r['event_date'] or 'no date'} · {r['location'] or '—'} · {r['status']}"
                )

    # ---------------------------------------------------------------- stats

    def _do_stats(self, opts):
        payload = {
            "work_live": Work.objects.filter(is_live=True).count(),
            "work_drafts": Work.objects.filter(is_live=False).count(),
            "packages": Package.objects.filter(is_live=True).count(),
            "commissions_total": Commission.objects.count(),
            "commissions_open": Commission.objects.filter(status__in=[
                Commission.Status.NEW, Commission.Status.READ, Commission.Status.QUOTED
            ]).count(),
            "commissions_new": Commission.objects.filter(status=Commission.Status.NEW).count(),
        }
        self.stdout.write(json.dumps(payload) if opts["json"] else "\n".join(
            f"{k}: {v}" for k, v in payload.items()
        ))
