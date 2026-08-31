# paulfrendach.com

One house, three rooms. A Django site for Paul Frendach — **Create** (Vision Oasis),
**Build** (web), **Train** (FRENDACH).

The brand is locked. The mark, colours, type, doctrine and sting come from the pack
in `brand/` and are not to be redesigned. Worlds change `--accent`, copy and imagery.
They never change the house mark.

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_house --slots 21
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

Admin is at `/admin/`. Mail prints to the console until `EMAIL_LIVE=1`.

## Shape

```
config/          settings, urls, wsgi/asgi
apps/house/      SiteConfig, World, Milestone, Inquiry — chrome, home, about, contact
apps/train/      FRENDACH: Law, SessionType, Slot, Booking + the booking JSON API
apps/create/     Vision Oasis: Work, Package
apps/build/      Web: Project, Capability
templates/       base + one folder per room, plus mail bodies
static/css/      house.css (tokens, chrome, components) · worlds.css (three skins)
static/marks/    the locked marks — do not edit
brand/           the locked pack: BRAND.md, DOCTRINE.md, ASSETS.md, tokens.css
```

## The rules that are enforced in code

- **One mark everywhere.** `templates/partials/chrome.html` is the only place the
  signature is built, and `apps/house/tests.py` fails if any room stops rendering it.
- **Nothing unconfirmed is printed.** `Milestone.confirmed` gates the honour line;
  unconfirmed items live in the admin and never reach a template.
- **A booking is a request.** `Booking` is created `pending`. Confirmation is a human
  act in the admin, not a side effect of a form submit.
- **Live switches.** Everything with content has `is_live`, so nothing ships early.

## The Train API

Read-only JSON, used by the booking UI and shown as a worked example in Build.

| Endpoint | Returns |
|---|---|
| `GET /train/api/sessions/` | session types, price labels, durations |
| `GET /train/api/slots/?session=<slug>&limit=<n>` | open slots with seats left and a book URL |
| `GET /train/api/bookings/<reference>/` | one booking's status |

## Mark geometry (read before touching the signature)

The locked rule is *RENDACH cap height = mark ink height, baselines aligned*.
`pf-house.svg` carries 6.9% clearspace on each edge, so its ink is 0.862 of the
rendered box. Fraunces cap height is 0.701em, and the master lockup
(`pf-signature-bone.png`) sets the fused ꟼF at 1.048 × cap. Therefore:

```
img height = 1.048 × 0.701 / 0.862 = 0.852em
```

The snippet in `brand/BRAND.md` says `1.14em`, which draws the mark about 34%
oversized against its own construction rule. `house.css` uses the derived value.

## Deploy

Set `DJANGO_DEBUG=0`, a real `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` and
`DJANGO_CSRF_TRUSTED_ORIGINS`, then `collectstatic`. WhiteNoise serves hashed,
compressed static in production; SQLite is fine to start and swaps for Postgres
by changing `DATABASES` alone.
