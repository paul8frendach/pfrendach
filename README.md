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
                 curtain.css (the opening page)
static/js/       clockwork.js (the movement) · sting.js (the curtain) · house.js
static/marks/    the locked marks — do not edit
brand/           the locked pack: BRAND.md, DOCTRINE.md, ASSETS.md, tokens.css
```

## The opening page

The site opens on the sting, drawn live in HTML/CSS — **not** a video element.
`static/js/clockwork.js` is a vanilla port of the studio's `logo-flash.tsx`:
balance wheel at 1 Hz, 15-tooth escape, 16/10 train, slider-crank r=26 rod=70.
`sting.js` runs the locked REST → HOLD choreography at 2.4x, so the visitor
waits about four seconds rather than ten. At HOLD the lockup flies into the
header signature and the curtain lifts — one continuous move, no cut.

- Plays once per session (`sessionStorage`), and is skippable by click, key,
  scroll or touch.
- `prefers-reduced-motion` snaps to HOLD and lifts.
- One P in the DOM, ever. The F seats into it at the locked −0.32em overlap.
- `/flash/` renders the same sting boxed, for screen-recording.
- The mp4 masters stay in `static/flash/` for graphics work. They are not
  played on the site.

The same movement runs quietly behind every room's hero (`[data-dial]`), and
the pages borrow its parts: chapter-ring rules (`.tickrule`), jewel markers
(`.beat`), gold hairlines, the vignette.

## Moving between rooms

`static/js/router.js` swaps `[data-main]` and nothing else. The chrome stays
put, the background movement keeps running (the same DOM node, never
re-mounted), and `--accent` is a registered custom property so gold, glow and
steel *morph* into each other instead of cutting.

- Links prefetch on hover or touch, so a room change is usually instant.
- On a touch screen, swipe left/right to move between the three rooms.
- Anything unexpected — a bad status, a missing `[data-main]` — falls back to
  an ordinary browser navigation rather than trapping the visitor.
- `/flash/` is excluded: it loads its own script, and only `main` is swapped.
- Pages containing a CSRF token are never cached.

## Density — how a long page is solved

A portfolio has a lot of important information and almost no permission to make
someone scroll for it. Four shared components carry that load; the worlds
restyle them but never re-implement them.

| Component | Job | Where |
|---|---|---|
| `.panels` (`[data-panels]`) | Step through blocks in place instead of stacking them | Train's doctrine (belief / laws / Mother's Law / record), Build's app rack |
| `.bento` + `.tile` | Varied tiles, one glance, no chaos | Train's offer, Create's commission |
| `.rail` | A horizontal run with scroll snap | Collections on narrow screens |
| `.fold` (`<details>`) | Summary always visible, depth on request | Build's API example |

Everything inside a panel is in the HTML on first render — panels only decide
what is on top, so search engines and JS-off visitors still get all of it.

The effect on the deepest pages, measured on a 390×844 phone:

| | Before | After |
|---|---|---|
| Train | 6.3 screens | 4.8 |
| Build | 5.0 | 4.2 |
| Create | 5.4 | 4.6 |

## The three rooms

They share the chrome, the mark and the movement. Everything else changes.

| | Create — Vision Oasis | Build — Web | Train — FRENDACH |
|---|---|---|---|
| Accent | Glow `#C6E04A` | Steel `#8FB4C4` | Gold `#E8C36A` |
| Ground | Night glow, heavier grain | Blueprint grid | Locker seams, a chalked touchline |
| Type | Fraunces with WONK on | Fraunces + mono annotations | Anton and Oswald, inside Train only |
| Shape | A contact sheet: film strip, burned-in slates, 2.39:1 plates | A drawing office: spec blocks, square corners | A locker bank: brushed plates, rivets, kit numbers |
| Content | Methods, the reel, what a small business can commission | Apps and the features inside them, off-the-shelf pieces | Doctrine, the Seven Laws, the offer, open slots |

Build's rack is tabs, not a scroll: pick an app on the left, its shipped
features render on the right, and the room stays on one screen.

Work in Create can carry an Instagram post or reel — paste the public URL and
the embed is derived from it (`Work.instagram_embed`).

## Chrome

Centred, and it condenses. At the top of a page it stands as a stacked
nameplate: signature, then the three worlds, then About and Contact as
sub-text. On the first scroll it collapses to a slim bar — signature left,
the three worlds still dead-centre. On a phone the condensed bar is 53px
(6% of the viewport) and carries the mark alone plus the three worlds.

The three worlds sit in a wide open rail with one lit jewel sliding beneath
them. It rests under the active room, follows the pointer, and takes that
room's colour. It re-seats after fonts load, on resize, all the way along the
condensation ramp, and after every room change — tab widths are decided by
type metrics, and those arrive late.

About and Contact are furniture, not worlds: off the centre axis, at the
rail's right edge, in the quietest type on the page, and retired to the footer
entirely on a phone.

### Why it does not judder

Two rules, and both are load-bearing:

1. **The chrome is `position: fixed`, with `.chrome__spacer` holding its
   expanded height in the flow.** A sticky bar that changes height changes the
   document height, which shifts the scroll position, which re-runs the
   collapse. That feedback loop *is* the judder.
2. **Condensation is one continuous variable, `--cond` (0 to 1 over 90px of
   scroll), not a class toggle.** Every dimension in the bar is expressed in
   terms of it. The signature exists twice — large in the crest, small at the
   rail's left — and they cross-fade, so no element ever jumps between two
   layouts.

## Presence

The page should feel like it knows someone is there, the way a painted portrait
follows you across a room — and never like it is chasing the cursor.

Two variables are published once per frame, eased rather than snapped:
`--px`/`--py` (pointer across the viewport) and `--pdx`/`--pdy` (the same,
signed from centre). A single delegated listener writes `--mx`/`--my` on
whatever the pointer is over. Nothing else listens.

What reads them: the movement leans a few pixels toward the viewer; the
world's light follows the pointer across the ground; Build's blueprint grid
shifts like a sheet on a desk; tiles and cards light from wherever the cursor
sits on them. All of it is gated on `(hover: hover) and (pointer: fine)` and on
reduced-motion, and every variable defaults to centre — a touch device or a
failed script leaves the page composed, not broken.

The one motion nobody triggers directly: opening a room sweeps that world's
light across the ground once.

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
