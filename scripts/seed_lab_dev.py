#!/usr/bin/env python
"""Seed a local LAB account that the Frendach Train tab can be built against.

    <LAB venv python> scripts/seed_lab_dev.py            # seed, reuse key
    <LAB venv python> scripts/seed_lab_dev.py --rotate   # issue a fresh key

WHY THIS EXISTS
    The Train tab is a wrapper over The LAB's public API, and an API you cannot
    stand up from scratch is an API you cannot onboard a second coach onto. This
    script is the reproducible half of that promise: one command takes an empty
    LAB dev database to a coach who has Pro, an intake form, published services
    and a working test key.

WHAT IT DELIBERATELY DOES NOT DO
    It never touches production and it never mints a `lab_live_` key. Everything
    it creates is a `lab_test_` credential against a local database, because the
    first six submissions of any integration are junk and they should not land
    in a real coach's inbox (docs/FINDTHE90_INTEGRATION.md, §7).

    It is idempotent. Running it twice changes nothing except, with --rotate,
    the key.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

LAB_REPO = Path(os.environ.get("LAB_REPO", "/Users/paulfrendach/-virtualenvs/TheLAB"))
LAB_DB = os.environ.get("LAB_DB_NAME", "thelab_demo")
PF_REPO = Path(__file__).resolve().parent.parent

COACH_USERNAME = "frendach_demo"
COACH_EMAIL = "frendach_demo@thelab.test"
KEY_LABEL = "paulfrendach.com (dev)"

# The Train storefront, expressed as LAB services. `packages` empty means the
# service is enquiry-only, which is how "On request" survives the trip: The LAB
# reports booking.mode = "enquiry" for a service with nothing to price, and the
# site invites a message instead of drawing a calendar it cannot fill.
SERVICES = [
    {
        "title": "1v1 Session",
        "type": "Training",
        "minutes": 60,
        "pricing_mode": "fixed",
        "per_athlete": True,
        "description": "One player, one hour, full attention. The ball never stops moving.",
        "packages": [(1, Decimal("85.00"))],
    },
    {
        "title": "Small Group",
        "type": "Training",
        "minutes": 75,
        "pricing_mode": "tiered",
        "per_athlete": True,
        "description": "Three or four players. Competitive reps, real tempo, nowhere to hide.",
        # (athletes, price PER ATHLETE) — the row stores the session total.
        "packages": [(2, Decimal("45.00")), (3, Decimal("45.00")), (4, Decimal("45.00"))],
    },
    {
        "title": "Film Session",
        "type": "Training",
        "minutes": 90,
        "pricing_mode": "fixed",
        "per_athlete": True,
        "description": "Filmed training, then the clips back with the reasons attached.",
        "packages": [(1, Decimal("150.00"))],
    },
    {
        "title": "Six-Week Block",
        "type": "Training",
        "minutes": 60,
        "pricing_mode": "fixed",
        "per_athlete": True,
        "description": "One session a week for six weeks, with work set for the hours in between.",
        "packages": [],  # enquiry-only: "On request"
    },
]

# The custom questions. These are the point of `GET /intake-form`: a question
# added here appears on paulfrendach.com with no deploy, so it is worth seeding
# a couple that a hand-built form would never have guessed.
INTAKE_FIELDS = [
    {"label": "What position do you play?", "field_type": "dropdown", "is_required": True,
     "is_per_athlete": True,
     "options": ["Goalkeeper", "Centre-back", "Full-back", "Midfield", "Winger", "Striker"]},
    {"label": "Current club or school team", "field_type": "short_text",
     "is_required": False, "is_per_athlete": True, "options": []},
    {"label": "What do you most want to work on?", "field_type": "long_text",
     "is_required": False, "is_per_athlete": True, "options": []},
    {"label": "How did you hear about Frendach?", "field_type": "multiple_choice",
     "is_required": False, "is_per_athlete": False,
     "options": ["Word of mouth", "Instagram", "A coach", "Played against him", "Other"]},
]


def bootstrap_django() -> None:
    if not (LAB_REPO / "manage.py").exists():
        sys.exit(f"No LAB checkout at {LAB_REPO}. Set LAB_REPO.")
    os.environ["DB_NAME"] = LAB_DB
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "thelab.settings")
    sys.path.insert(0, str(LAB_REPO))
    os.chdir(LAB_REPO)
    import django
    django.setup()


def ensure_cache_table() -> None:
    """The API's rate limiter writes to the cache, and this project's cache is a
    database table. `createcachetable` is NOT a migration, so a clean `migrate`
    leaves it missing and every endpoint 500s on `django_cache doesn't exist` -
    which reads like a broken API rather than a missing setup step."""
    from django.core.management import call_command
    call_command("createcachetable", verbosity=0)


def seed_coach():
    from django.contrib.auth import get_user_model
    User = get_user_model()
    coach, created = User.objects.get_or_create(
        username=COACH_USERNAME,
        defaults={"email": COACH_EMAIL, "first_name": "Paul", "last_name": "Frendach"},
    )
    coach.email = COACH_EMAIL
    coach.first_name, coach.last_name = "Paul", "Frendach"
    coach.coach = True          # comp_pro refuses a non-coach
    coach.set_password("frendach-dev-2026")
    coach.save()
    return coach, created


def seed_pro(coach):
    """Comped Pro. The API re-checks this on EVERY request, not just at key
    creation, so a lapsed subscription reads as 403 subscription_required."""
    from payments.models import Subscription
    sub, created = Subscription.objects.get_or_create(
        subscriber=coach, subscription_type="coach_lab", target_coach=None,
        defaults={
            "status": "active", "is_comped": True,
            "comp_note": "Local dev seed for the paulfrendach.com wrapper.",
        },
    )
    if not created and (sub.status != "active" or not sub.is_comped):
        sub.status, sub.is_comped = "active", True
        sub.comp_note = "Local dev seed for the paulfrendach.com wrapper."
        sub.save()
    return sub


def seed_services(coach):
    from page.models import CoachSport, Package, Service, ServiceDuration, Sport
    sport, _ = Sport.objects.get_or_create(sport="Soccer")
    CoachSport.objects.get_or_create(coach=coach, sport=sport)

    made = []
    for spec in SERVICES:
        service, _ = Service.objects.get_or_create(
            owner=coach, sport=sport, type=spec["type"], title=spec["title"],
            defaults={
                "duration": timedelta(minutes=spec["minutes"]),
                "pricing_mode": spec["pricing_mode"],
                "is_per_athlete": spec["per_athlete"],
                "description": spec["description"],
            },
        )
        service.duration = timedelta(minutes=spec["minutes"])
        service.pricing_mode = spec["pricing_mode"]
        service.is_per_athlete = spec["per_athlete"]
        service.description = spec["description"]
        service.save()

        if not spec["packages"]:
            made.append((service, 0))
            continue

        duration, _ = ServiceDuration.objects.get_or_create(
            service=service, duration=timedelta(minutes=spec["minutes"]),
            defaults={"ordering": 0},
        )
        for athletes_n, per_athlete in spec["packages"]:
            Package.objects.update_or_create(
                service=service, athletes=athletes_n, service_duration=duration,
                defaults={"price": per_athlete * athletes_n},
            )
        made.append((service, len(spec["packages"])))
    return made


def seed_intake(coach):
    from page.models import CallToAction, IntakeField
    cta, _ = CallToAction.objects.get_or_create(
        user=coach, defaults={"cta_type": "intake_form", "text": "Start training"},
    )
    cta.cta_type = "intake_form"
    cta.text = "Start training"
    cta.is_enabled = True
    # Every toggle on: this is the "maximise what reaches the coach's account"
    # half of the brief. Each one is a field the wrapper will render and post.
    cta.collect_athlete_name = True
    cta.collect_parent_name = True
    cta.collect_email = True
    cta.collect_phone = True
    cta.collect_age = True
    cta.collect_experience = True
    cta.collect_notes = True
    cta.save()

    for order, spec in enumerate(INTAKE_FIELDS):
        IntakeField.objects.update_or_create(
            cta=cta, label=spec["label"],
            defaults={
                "field_type": spec["field_type"], "is_required": spec["is_required"],
                "is_per_athlete": spec["is_per_athlete"], "options": spec["options"],
                "order": order,
            },
        )
    return cta


def issue_key(coach, *, rotate: bool):
    # Mint exactly what Settings -> API keys mints. LabApiKey.issue() falls back
    # to a narrow ['intake:read', 'leads:write'] pair, which is NOT what a coach
    # gets from the screen - and a key short a scope surfaces days later as a
    # 403 in the integrator's console, not here (docs/FINDTHE90_INTEGRATION.md).
    from api.keys_ui import DEFAULT_SCOPES
    from api.models import LabApiKey
    existing = LabApiKey.objects.filter(
        owner_user=coach, label=KEY_LABEL, is_active=True, revoked_at__isnull=True,
    ).first()
    if existing and not rotate:
        return None, existing
    if existing and rotate:
        from django.utils import timezone
        existing.is_active = False
        existing.revoked_at = timezone.now()
        existing.save(update_fields=["is_active", "revoked_at"])
    key, raw = LabApiKey.issue(
        owner_user=coach, label=KEY_LABEL, is_test=True, created_by=coach,
        scopes=DEFAULT_SCOPES,
    )
    return raw, key


def write_env(raw_key: str | None) -> None:
    """Put the key where the site reads it. Only ever writes a test key."""
    if not raw_key:
        return
    env_path = PF_REPO / ".env"
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    wanted = {
        "LAB_API_BASE": "http://127.0.0.1:8011",
        "LAB_API_KEY": raw_key,
    }
    for name, value in wanted.items():
        pattern = re.compile(rf"^{name}=")
        for i, line in enumerate(lines):
            if pattern.match(line):
                lines[i] = f"{name}={value}"
                break
        else:
            lines.append(f"{name}={value}")
    env_path.write_text("\n".join(lines) + "\n")
    print(f"  wrote LAB_API_BASE + LAB_API_KEY to {env_path}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rotate", action="store_true",
                    help="Revoke the existing dev key and issue a new one.")
    args = ap.parse_args()

    bootstrap_django()
    from payments.models import is_pro_coach

    print(f"LAB   : {LAB_REPO}")
    print(f"DB    : {LAB_DB}\n")

    ensure_cache_table()
    print("cache : django_cache table present")

    coach, created = seed_coach()
    print(f"coach : {coach.username} ({'created' if created else 'existing'})")

    seed_pro(coach)
    print(f"pro   : {is_pro_coach(coach)}  (comped)")

    services = seed_services(coach)
    for service, n in services:
        note = f"{n} package(s)" if n else "enquiry-only"
        print(f"  svc : {service.display_title} — {note}")

    cta = seed_intake(coach)
    print(f"intake: '{cta.text}' + {cta.fields.count()} custom question(s)")

    raw, key = issue_key(coach, rotate=args.rotate)
    if raw:
        print(f"\nkey   : {raw}")
        print("        ^ shown once. Stored hashed.")
        write_env(raw)
    else:
        print(f"\nkey   : {key.prefix}… already exists ({key.label})")
        print("        Re-run with --rotate to replace it.")

    print("\nNext: run the LAB on :8011, then")
    print("  curl -s -H 'Authorization: Bearer <key>' \\")
    print("       -H 'User-Agent: paulfrendach.com/1.0' \\")
    print("       http://127.0.0.1:8011/api/v1/me")


if __name__ == "__main__":
    main()
