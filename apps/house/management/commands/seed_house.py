"""
Seed the house with real, locked content.

Everything written here comes from the brand pack. Nothing invented: no fake
testimonials, no unlocked honors, no clients he does not have. Unconfirmed
milestones are loaded but flagged so they never print.

    python manage.py seed_house
    python manage.py seed_house --slots 21   # also lay 3 weeks of open slots
"""

from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.build.models import Capability, Feature, Project
from apps.create.models import Method, Package, Work
from apps.house.models import Milestone, SiteConfig, World
from apps.train.models import Law, SessionType, Slot

WORLDS = [
    {
        "slug": "create",
        "name": "Vision Oasis",
        "verb": "Create",
        "descriptor": "Content & cinema",
        "kicker": "Create — Vision Oasis",
        "headline": "Cinema first. Useful second.",
        "lead": "Session films, brand films, stills. Night, grain, breath, the walk-off.",
        "card_line": "Films and stills made the way the training is made. Never stock.",
        "cta_label": "See the reel",
        "sort": 10,
    },
    {
        "slug": "build",
        "name": "Web",
        "verb": "Build",
        "descriptor": "Design and development",
        "kicker": "Build — Web",
        "headline": "Quiet pages. Sharp objects.",
        "lead": "Design-to-build in one pair of hands. No template sludge.",
        "card_line": "Sites and software for people who care how it actually works.",
        "cta_label": "See the work",
        "sort": 20,
    },
    {
        "slug": "train",
        "name": "FRENDACH",
        "verb": "Train",
        "descriptor": "Soccer training",
        "kicker": "Train — FRENDACH",
        "headline": "Love the process.",
        "lead": "Train players who love the game enough to become themselves inside it.",
        "card_line": "Small roster. High school first. Film is part of the method.",
        "cta_label": "Book a session",
        "sort": 30,
    },
]

LAWS = [
    (1, "Order", "The session is where chaos can be put down. One place in the week that makes sense."),
    (2, "The Next Team", "Mother's Law. Once you are the best on the team, it is getting to be time to go."),
    (3, "Touches", "The hours the team does not see. Touches, touches, touches. They build mental awareness like nothing else."),
    (4, "Body / Ball", "How the ball feels, how to strike it, which direction the spin is. A player has to know how his body and the ball relate."),
    (5, "The Margin", "At the top, technique evens out. Freedom under tension does not."),
    (6, "A Tool", "A game used to build a life, not just a body and a trophy."),
    (7, "The Weather", "No high on the highs, no collapse on the lows. Love means you accept both."),
]

SESSIONS = [
    {
        "name": "1v1 Session",
        "slug": "1v1-session",
        "format": SessionType.Format.ONE_TO_ONE,
        "summary": "One player, one hour, full attention. The ball never stops moving.",
        "description": (
            "Built around what the player actually needs that week, not a stock plan. "
            "Warm-up into technical work, then the same skill under pressure — because "
            "the difference at the top is doing it while someone is on your back."
        ),
        "focus": "First touch under pressure\nStriking: laces, inside, spin\nScanning before you receive\nOne foot you avoid, made usable",
        "duration_minutes": 60,
        "capacity": 1,
        "price": 85,
        "sort": 10,
    },
    {
        "name": "Small Group",
        "slug": "small-group",
        "format": SessionType.Format.SMALL_GROUP,
        "summary": "Three or four players. Competitive reps, real tempo, nowhere to hide.",
        "description": (
            "Numbers small enough that everyone is on the ball constantly and Paul can "
            "still coach each player by name. Rondos, duels, finishing under fatigue."
        ),
        "focus": "Duels and 1v1s\nCombination play in tight space\nFinishing tired\nCompeting without losing the head",
        "duration_minutes": 75,
        "capacity": 4,
        "price": 45,
        "sort": 20,
    },
    {
        "name": "Film Session",
        "slug": "film-session",
        "format": SessionType.Format.FILM,
        "summary": "Filmed training, then the clips back with the reasons attached.",
        "description": (
            "Film is part of the method, not a highlight service. The session is shot, "
            "then reviewed together: what you saw, what was actually there, and what "
            "the next rep should look like. You keep the footage."
        ),
        "focus": "Filmed technical block\nClip review with the why\nOne habit named for the month\nFootage you keep",
        "duration_minutes": 90,
        "capacity": 1,
        "price": 150,
        "requires_film": True,
        "sort": 30,
    },
    {
        "name": "Six-Week Block",
        "slug": "six-week-block",
        "format": SessionType.Format.BLOCK,
        "summary": "One session a week for six weeks, with work set for the hours in between.",
        "description": (
            "The one that actually changes a player. Six sessions, homework between them, "
            "and film at the start and the end so the difference is visible rather than felt."
        ),
        "focus": "Six sessions, one a week\nWork set for the off hours\nFilm at week one and week six\nA plan for the next team",
        "duration_minutes": 60,
        "capacity": 1,
        "price": None,
        "price_note": "On request",
        "sort": 40,
    },
]

MILESTONES = [
    # confirmed: public-safe per the pack.
    ("", "DeMatha Catholic", "Central midfielder", True, 10),
    ("", "Baltimore Celtic", "Club", True, 20),
    ("2018", "Maryland — NCAA champions", "Roster, limited minutes", True, 30),
    ("", "Temple", "Starter, captain", True, 40),
    ("", "Gatorade nominee", "", True, 50),
    # not confirmed: held back until Paul says so. These never render.
    ("", "USYS national title", "Awaiting confirmation", False, 60),
    ("", "Maryland State Cup", "Awaiting confirmation", False, 70),
    ("2018", "Gatorade Player of the Year", "Awaiting confirmation", False, 80),
]

PACKAGES = [
    {
        "name": "Session Film",
        "slug": "session-film",
        "summary": "One training session, shot and cut like a short film.",
        "deliverables": "60–90s edit\n3 vertical cutdowns\n10 graded stills\nRaw selects on request",
        "turnaround": "1 week",
        "price_from": 450,
        "sort": 10,
    },
    {
        "name": "Brand Film",
        "slug": "brand-film",
        "summary": "A film about what you actually do, made over a real day.",
        "deliverables": "Pre-production and shot list\nFull shoot day\n90–120s film\nSocial cutdowns\nStills set",
        "turnaround": "3 weeks",
        "price_from": 1800,
        "sort": 20,
    },
    {
        "name": "Stills Set",
        "slug": "stills-set",
        "summary": "Portraits and action stills with the same eye as the films.",
        "deliverables": "2-hour shoot\n25 graded frames\nUsage for web and social",
        "turnaround": "1 week",
        "price_from": 400,
        "sort": 30,
    },
]

METHODS = [
    {
        "name": "The look",
        "kicker": "01",
        "blurb": "Before a camera comes out: what this place actually feels like, and which hour of the day says it.",
        "detail": "A reference set and a shot list, so the shoot day is spent shooting.",
        "gear": "References, shot list, location scout",
        "sort": 10,
    },
    {
        "name": "The shoot",
        "kicker": "02",
        "blurb": "One camera, natural light where possible, and the patience to wait for the moment rather than stage it.",
        "detail": "Long lenses for the real thing, wide for the room. Sound recorded properly, not as an afterthought.",
        "gear": "Mirrorless body, primes, gimbal, drone, lav + shotgun",
        "sort": 20,
    },
    {
        "name": "The cut",
        "kicker": "03",
        "blurb": "Story before effects. The edit is where a day of footage becomes ninety seconds someone finishes watching.",
        "detail": "Grade, sound design and a mix that survives a phone speaker.",
        "gear": "Resolve, grade, sound design, -14 LUFS mix",
        "sort": 30,
    },
    {
        "name": "The delivery",
        "kicker": "04",
        "blurb": "Cut for where it is going: a wide film for the site, verticals for the feed, stills for everything else.",
        "detail": "Every crop framed on purpose, not exported from the same timeline and hoped for.",
        "gear": "16:9, 4:5, 9:16, stills set",
        "sort": 40,
    },
]

CAPABILITIES = [
    {
        "title": "Booking and confirmation",
        "blurb": "Session types, open slots, seat limits, and a request flow that hands the client a reference and the owner a decision.",
        "detail": "Running live in the Train room of this site, backed by a JSON API.",
        "glyph": "01",
        "sort": 10,
    },
    {
        "title": "Brand systems in code",
        "blurb": "One token file, many skins. Sub-brands change accent, copy and imagery without a second codebase to maintain.",
        "detail": "This site is the demonstration: three worlds, one stylesheet.",
        "glyph": "02",
        "sort": 20,
    },
    {
        "title": "Media pipelines",
        "blurb": "Upload, transcode, thumbnail, and publish. Video handled properly instead of dropped into a page and hoped for.",
        "glyph": "03",
        "sort": 30,
    },
    {
        "title": "Content and CMS",
        "blurb": "An admin the owner can actually use, with a live switch on everything so nothing ships before it is ready.",
        "glyph": "04",
        "sort": 40,
    },
    {
        "title": "Inbound and inbox",
        "blurb": "Forms that survive bots, land as records, and notify a real person — not a contact page that quietly loses work.",
        "glyph": "05",
        "sort": 50,
    },
    {
        "title": "Ship and keep it up",
        "blurb": "Deploy, static assets, HTTPS, backups, and the boring parts that decide whether a site is still standing in a year.",
        "glyph": "06",
        "sort": 60,
    },
]

PROJECTS = [
    {
        "name": "paulfrendach.com",
        "slug": "paulfrendach-com",
        "tagline": "One house, three worlds, and a booking system underneath it.",
        "role": "Brand system, design, build",
        "year": "2026",
        "stage": Project.Stage.LIVE,
        "stack": "Django, SQLite, WhiteNoise, vanilla CSS, vanilla JS",
        "problem": (
            "Three trades — content, web, training — that share one person and one mark, "
            "but read as three different businesses if you build them as three sites."
        ),
        "approach": (
            "One Django project, one stylesheet, one locked house mark. Worlds are a "
            "data attribute that swaps the accent, the copy and the rhythm. The Train "
            "room carries a real booking flow with slots, seat limits and confirmations."
        ),
        "outcome": "A single codebase where a new room costs a template, not a rebuild.",
        "is_featured": True,
        "sort": 10,
    },
]


FEATURES = [
    ("paulfrendach-com", "The curtain", "The locked sting drawn live in HTML and CSS, not played from a video file. Lifts into the header signature.", "~4s, once per session"),
    ("paulfrendach-com", "Three worlds, one stylesheet", "A data attribute swaps accent, texture and rhythm. A new room costs a template, not a rebuild.", "1 CSS system"),
    ("paulfrendach-com", "Seamless routing", "Links swap the page body only. The background movement never restarts and prefetch makes a room change instant.", "No reload"),
    ("paulfrendach-com", "Booking and confirmation", "Session types, open slots, seat limits, a reference for the client and a decision for the owner.", "Seat-safe under load"),
    ("paulfrendach-com", "Read-only JSON API", "Sessions, open slots and booking status as public endpoints, ready for a widget or an app.", "3 endpoints"),
    ("paulfrendach-com", "An admin he can use", "Live switches on everything, so nothing ships before he says so — including unconfirmed honours.", "0 code edits to publish"),
]


class Command(BaseCommand):
    help = "Load the locked house content. Safe to run repeatedly."

    def add_arguments(self, parser):
        parser.add_argument(
            "--slots",
            type=int,
            default=0,
            help="Lay this many open slots across the coming weeks.",
        )

    def handle(self, *args, **options):
        SiteConfig.load()

        for data in WORLDS:
            World.objects.update_or_create(slug=data["slug"], defaults=data)
        self.stdout.write(self.style.SUCCESS(f"Worlds: {World.objects.count()}"))

        for number, title, body in LAWS:
            Law.objects.update_or_create(
                number=number, defaults={"title": title, "body": body}
            )
        self.stdout.write(self.style.SUCCESS(f"Laws: {Law.objects.count()}"))

        for data in SESSIONS:
            SessionType.objects.update_or_create(slug=data["slug"], defaults=data)
        self.stdout.write(self.style.SUCCESS(f"Session types: {SessionType.objects.count()}"))

        for year, title, detail, confirmed, sort in MILESTONES:
            Milestone.objects.update_or_create(
                title=title,
                defaults={"year": year, "detail": detail, "confirmed": confirmed, "sort": sort},
            )
        held = Milestone.objects.filter(confirmed=False).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Milestones: {Milestone.objects.count()} ({held} held back until confirmed)"
            )
        )

        for data in PACKAGES:
            Package.objects.update_or_create(slug=data["slug"], defaults=data)
        for data in METHODS:
            Method.objects.update_or_create(name=data["name"], defaults=data)
        for data in CAPABILITIES:
            Capability.objects.update_or_create(title=data["title"], defaults=data)
        for data in PROJECTS:
            Project.objects.update_or_create(slug=data["slug"], defaults=data)
        for index, (slug, title, blurb, metric) in enumerate(FEATURES):
            project = Project.objects.filter(slug=slug).first()
            if project is None:
                continue
            Feature.objects.update_or_create(
                project=project,
                title=title,
                defaults={"blurb": blurb, "metric": metric, "sort": (index + 1) * 10},
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Create packages: {Package.objects.count()} · "
                f"Methods: {Method.objects.count()} · "
                f"Features: {Feature.objects.count()} · "
                f"Capabilities: {Capability.objects.count()} · "
                f"Projects: {Project.objects.count()} · "
                f"Work: {Work.objects.count()}"
            )
        )

        if options["slots"]:
            self._lay_slots(options["slots"])

    def _lay_slots(self, count: int) -> None:
        """A plausible week: weekday evenings, Saturday mornings. Editable in admin."""
        pattern = [
            # weekday (Mon=0), local time, session slug
            (1, time(17, 30), "1v1-session"),
            (1, time(18, 45), "small-group"),
            (3, time(17, 30), "1v1-session"),
            (3, time(18, 45), "film-session"),
            (5, time(9, 0), "1v1-session"),
            (5, time(10, 15), "small-group"),
            (5, time(11, 30), "1v1-session"),
        ]
        sessions = {s.slug: s for s in SessionType.objects.all()}
        today = timezone.localtime().date()
        made = 0
        week = 0
        while made < count and week < 12:
            monday = today + timedelta(days=(7 - today.weekday()) + week * 7)
            for weekday, at, slug in pattern:
                if made >= count:
                    break
                session = sessions.get(slug)
                if session is None:
                    continue
                naive = timezone.datetime.combine(monday + timedelta(days=weekday), at)
                starts_at = timezone.make_aware(naive)
                _, created = Slot.objects.get_or_create(
                    session_type=session,
                    starts_at=starts_at,
                    defaults={
                        "capacity": session.capacity,
                        "location": "Southern Maryland",
                    },
                )
                if created:
                    made += 1
            week += 1
        self.stdout.write(self.style.SUCCESS(f"Slots laid: {made}"))
