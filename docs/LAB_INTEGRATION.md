# The Train room, on The LAB's API

**Status: working document.** Step one of three is built and tested end to end
(services, intake, leads). Booking, payment and film are not — §7 says what is
missing and in what order.

| | |
|---|---|
| Last updated | 2026-08-31 |
| LAB branch | `staging` @ `c3c0c748` |
| Wrapper | `apps/lab/`, consumed by `apps/train/` |
| Local LAB | `/Users/paulfrendach/-virtualenvs/TheLAB`, DB `thelab_demo`, port 8011 |
| Production | `https://www.thelabplatform.com` — **the `www.` is required**, see §6 |

---

## 1. What this is

The Train room used to be its own storefront: `SessionType` rows in this repo's
database, priced here, edited here. It is now a **wrapper over The LAB's public
API**. Paul's services, prices and intake questions live in his LAB account, and
this site renders them.

The property that makes this worth doing: **a thing the coach changes in The LAB
changes on the website without a deploy.** A hand-maintained page always ends up
advertising last summer.

The property that makes it safe: **a key only ever touches its owner's data.**
There is no `coach` parameter anywhere in the API, so a bug on this side cannot
reach another coach's account.

And the reason it is built as a reusable app rather than four view functions:
this is the first of these. `apps/lab/` knows nothing about Paul — point
`LAB_API_KEY` at another coach and the same code renders their storefront.

### The rule this codebase does not break

**Print prices, never compute them.** `GET /services` already applies the
coach's packages, tiers and price floors; `GET /price` answers for one specific
booking. Multiplying a rate here produces a number the coach's own checkout then
contradicts — in public, on their own page. `apps/lab/presenters.py` formats and
never arithmetics.

---

## 2. What a coach needs before any of this works

This is the onboarding checklist. It is in dependency order, and steps 1–2 are
the ones people get stuck on.

| # | Requirement | Where | If missing |
|---|---|---|---|
| 1 | A LAB account, marked as a coach | The LAB signup | Nothing else applies |
| 2 | **An active LAB Pro subscription** | Billing, or comped by Justin | **Every endpoint returns `403 subscription_required`** |
| 3 | An intake form (a `CallToAction`) | Their LAB page settings | `GET /intake-form` returns `404 no_intake_form`; the enquiry page shows "ask directly" |
| 4 | At least one published Service with a Package | Manage Services | `GET /services` returns `[]`; the tariff is empty |
| 5 | An API key | Settings → API keys | `401 missing_key` |
| 6 | *(for booking, later)* Locations, travel regions, availability | Manage Services / Availability | Services report `booking.mode = "enquiry"` rather than `"calendar"` |

**Pro is re-checked on every single request, not just when the key is made.**
If the coach lapses mid-season their website stops answering and nothing in this
repo can fix it. That is deliberate on The LAB's side — a paid feature that gets
paid for once is not a paid feature — and the error message says so plainly, so
it is not mistaken for a bug in our code.

### Issuing the key

The coach does this themselves. Nobody at The LAB is involved, and Paul never
needs the coach's password.

1. Log in to The LAB → **Settings → API keys**
2. Label it for the site it is for — `"paulfrendach.com"`, `"findthe90.com"`
3. Tick **test key** while it is being built
4. **Copy it now.** Only a SHA-256 hash is stored; it is never shown again
5. Paste it into that site's server environment as `LAB_API_KEY`

The key can be revoked by the coach at any time, without asking anyone.

**Scopes:** a key from that screen carries all four — `intake:read`,
`leads:write`, `services:read`, `signup:write`. They are not offered as choices
any more, because the coach is not the person writing the integration and a key
short a scope surfaces days later as a 403 in someone else's console. Keys minted
before that change carry narrower lists and still work as issued.

> **Trap, found the hard way.** `LabApiKey.issue()` falls back to only
> `['intake:read', 'leads:write']` when no scopes are passed. That is *not* what
> the coach's screen mints. Anything creating keys programmatically must pass
> `api.keys_ui.DEFAULT_SCOPES`, or `/services` 403s while `/me` looks perfect.
> `scripts/seed_lab_dev.py` does.

### Test keys vs live keys

A `lab_test_` key writes real leads, flagged `test:` in their source. The coach
sees them and can tell them apart. **Build on a test key** — the first six
submissions of any integration are junk and should not fill a real inbox.

---

## 3. Reproducing this setup from scratch

Two servers: The LAB on `:8011`, this site on `:8012`.

```bash
# 1. The LAB, up to date and migrated
cd ~/-virtualenvs/TheLAB
git pull                                   # see the note in §6 about skip-worktree
DB_NAME=thelab_demo venv/bin/python manage.py migrate
DB_NAME=thelab_demo venv/bin/python manage.py createcachetable

# 2. Seed a coach who has Pro, an intake form, services and a test key.
#    Idempotent. Writes LAB_API_BASE + LAB_API_KEY into this repo's .env.
cd ~/Desktop/paulfrendach
~/-virtualenvs/TheLAB/venv/bin/python scripts/seed_lab_dev.py

# 3. Run The LAB
cd ~/-virtualenvs/TheLAB
DB_NAME=thelab_demo venv/bin/python manage.py runserver 127.0.0.1:8011

# 4. Run this site (separate shell)
cd ~/Desktop/paulfrendach && .venv/bin/python manage.py runserver 127.0.0.1:8012
```

Prove the wiring before writing anything:

```bash
curl -s -H "Authorization: Bearer $LAB_API_KEY" \
     -H "User-Agent: paulfrendach.com/1.0" \
     http://127.0.0.1:8011/api/v1/me
```

`GET /me` takes two minutes and proves the key points at the right account. A
key on the wrong account is invisible until somebody asks where their enquiries
went.

`scripts/seed_lab_dev.py --rotate` revokes the dev key and issues a new one.

### Why `thelab_demo` and not `thelab_db`

`thelab_db` has a schema loaded from a dump and **one** row in
`django_migrations` against 382 migrations — so `migrate` cannot be used on it
at all. `thelab_demo` was built by a clean `migrate` and has real history. Use
it. (`createcachetable` is a separate step because it is not a migration: the
API's rate limiter writes to a database cache table, and without it every
endpoint 500s on `django_cache doesn't exist`.)

---

## 4. What actually transfers to the coach's account

Verified end to end on 2026-08-31 — submitted through the rendered form, read
back out of the LAB database.

| From the form | Lands as | Notes |
|---|---|---|
| Parent name, email, phone | `Payer` | Phone normalised to E.164 |
| Player first/last name | `Athlete`, linked to the payer | `relationship = parent_guardian` |
| Age | **exactly one** of `age_range` / `birth_year` / `birthday` | Chosen per player by `age_type` |
| Custom per-player questions | `Lead.answers["per_athlete"][…]` | Keyed by the question's **label** |
| Custom one-off questions | `Lead.answers[…]` | |
| Notes | `Lead.notes` | The service they came from is appended |
| — | A chat thread with a lead card, an email, an in-app notification, the navbar red dot | `create_lead` runs the whole pipeline |

Up to **12 athletes** per enquiry (`api/views.py MAX_ATHLETES`), matched in
`apps/lab/intake.py` so an over-long submission is explained here rather than
silently truncated upstream.

### The one thing that does not transfer

**`experience` is accepted and stored nowhere.** `POST /leads` takes it per
athlete and `_clean_athletes` carries it through, but `Athlete` has no such
field, `create_athletes` never reads it, and it does not reach the lead card
either. It is silently dropped.

Our workaround, in `payload_from`: send it in the documented place *and* mirror
it into that athlete's `answers` as `"Experience so far"`, which is what the
coach actually sees today. When The LAB grows the field, the documented path
starts working and the mirror can go.

---

## 4a. Read against Paul's real account, 31 Aug 2026

What a live key actually found, and what it says about the onboarding list in §2.

| | |
|---|---|
| `GET /me` | `paulfrendach`, key "Frendach train", all four scopes, `mode: live`, Pro active |
| `GET /services` | **1** — Soccer Training, 60 min, `rate` mode, $70/hr, `booking.mode = "calendar"` |
| `GET /availability` | Real slots: Thursdays 18:00 at Don Henderson Field (Swarthmore), `America/New_York` |
| `GET /intake-form` | **`is_enabled: false`** — and phone, age and experience all off, zero custom fields |
| `GET /events` | empty |
| `GET /reviews` | empty, no Google Business Profile linked |
| `GET /style` | `no_style` |

Two things worth drawing out of that:

1. **Availability was ready before the intake form was.** The gap list in §2 is in
   dependency order for *setup*, not for *value*: this account could take a
   booking before it could take an enquiry. The site now reads real times on the
   Train index and the schedule page.
2. **A disabled intake form is invisible until you look.** It is not an error
   anywhere — the API answers `200` and the coach's own LAB page simply renders
   no "Get Started" button. The wrapper says "the enquiry form is closed just
   now" rather than showing an empty form, which is the only honest option.

## 4b. Getting a coach's services INTO The LAB

**The API has no write path for coach configuration.** Every `POST` it accepts
creates a customer-side object — a lead, a booking, a review, a film order, a
payment intent. Services, packages, durations, locations and the intake form are
read-only, by design: §1a of `docs/FINDTHE90_INTEGRATION.md` records the decision
that configuration *"flows outward from Manage Services"*, so one answer feeds
the coach's own page, the API, and every site built on it.

That is a real tension with what an integrator wants. The developer already
knows what the coach sells — it is on the page they were hired to replace — and
retyping it into Manage Services is both work and a chance to get it wrong.

`apps/lab/catalogue.py` is the half that can be built without that endpoint.

```bash
manage.py lab_catalogue                    # reconcile site against account
manage.py lab_catalogue --brief            # + Manage Services instructions
manage.py lab_catalogue --payload          # + the JSON a write endpoint would take
manage.py lab_catalogue --file catalogue/other-coach.json
```

One JSON file per coach declares what the **site** offers. The command reads what
the **account** holds, and reports:

| | |
|---|---|
| `match` | The site and the account agree |
| `drift` | Both have it and they disagree — **with both numbers printed**. This is the failure the whole thing exists to catch: the site quoting $85 while the account charges $70 |
| `missing` | Declared on the site, absent from the account. The site cannot sell it |
| `extra` | Live in the account, not offered on the site |

Then it **pushes back**. Anything described too thinly for The LAB to hold gets a
question written to be forwarded to the coach without editing — "Is that price
per player, or for the whole session however many turn up?" rather than
"`is_per_athlete` is required". Three severities:

- **BLOCKS** — the service cannot be created at all
- **DEGRADES** — it can, but it will not sell the way the coach expects (a
  missing location is this: The LAB reports the service as enquiry-only and no
  calendar can be drawn)
- **POLISH** — it will work, it just will not read as well

`--brief` prints Manage Services field by field, in the order the form asks, with
`— ASK —` where an answer is missing. That is the deliverable that works today: a
person can follow it without knowing the API exists.

`--payload` prints the shape a `POST /api/v1/services` would take, mirroring
`page.models.Service` / `ServiceDuration` / `Package`. **Nothing consumes it.** It
exists so the mapping is agreed and tested before the endpoint arrives, rather
than invented in a hurry on the day it does.

### What would have to change for real automation

Writing services over the API needs new endpoints on The LAB, and that is a
platform decision rather than an integration one — it reverses §1a's direction of
flow. Worth raising as a proposal rather than a patch, because the questions it
opens are the interesting part: does a website-created service appear in Manage
Services as the coach's own, or as something managed elsewhere and read-only to
them? What happens when the coach edits it afterwards and the site's file still
says the old thing? Which side wins a conflict? A write endpoint without an
answer to that last one produces exactly the drift this command was built to
detect.

## 4c. Prepaid blocks

The LAB grew a real product for these on 2026-09-01 (gap G3), and it changed how
the catalogue describes them.

**Six-Week Block used to sit in `catalogue/frendach.json` as a service with no
price**, which is why `lab_catalogue` refused to push it: "no pricing mode". The
shape was wrong, not the data. A block has no duration, no athlete tiers and no
location of its own — it is N sessions *of* a service. It now lives in a
`blocks` array pointing at its service by key, and the blocking question went
away.

```json
"blocks": [
  {"key": "six-week-block", "title": "Six-Week Block",
   "service_key": "1v1-session", "sessions": 6,
   "price": "459.00", "valid_weeks": 12}
]
```

`GET /api/v1/blocks` returns `sessions`, `price`, `price_per_session`,
`valid_weeks`, and a `saving` against buying singly that is **already computed**.
Do not recompute it: what one session costs depends on the coach's packages and
floors, and a site that multiplies will contradict the tariff directly above it.

Two traps in the payload:

- **`valid_weeks: null` means never expires, not zero weeks.** Printing "use
  within 0 weeks" from a null is the obvious way to get this wrong;
  `BlockCard.window_label` says "no expiry".
- **`saving: null` means there is nothing to claim.** "Save 0%" on a card reads
  as a bug, so the API sends null rather than a zero.

`purchase.mode` is `checkout` when the coach has a connected Stripe account, and
`enquiry` with reason `no_payout_account` when they do not — there is nowhere to
send the money, so invite a message rather than draw a checkout that cannot
finish.

**Buying:** `POST /api/v1/blocks/{id}/purchase-intent` returns a `client_secret`.
Mount Stripe's Payment Element against it; the card never touches this server.
**A successful Payment Element is not a completed purchase** — the block is
pending until The LAB's webhook confirms the money, and its sessions cannot be
spent before that. The response repeats it in `note`. Treating the browser as
proof of payment is the one way to get this badly wrong.

**The refund rule**, so a site can state it honestly: sessions already taken are
charged at the coach's ordinary single-session price and the rest comes back.
The bulk discount is earned by completing the block, not by starting one.

## 4d. Provisioning: create first, then verify

`manage.py lab_catalogue --push` runs in a deliberate order:

1. **Services first** — a block names the service it buys sessions of, and The
   LAB refuses one whose service is not there yet.
2. **Blocks** — naming its service by *your* `external_ref`, so a service and
   its blocks provision in one pass without waiting to learn what id The LAB
   allocated.
3. **Verify** — read the account back with the cache bypassed, and reconcile
   again.

Step 3 is what makes provisioning trustworthy, and it is not decoration.
Writing returns The LAB's word for what it did; verifying asks the account
itself and compares it to what this site is about to show a parent. On the
first real run every service reported `updated` and verification still said:

```
still differs  1v1 Session
               site expects bookable times, but LAB reports this as
               enquiry-only (usually a missing location)
```

The writes landed and the account still did not match, because the venue does
not exist on it and the API will not invent a location. Without the verify pass
that reads as a clean success.

## 5. Where things are

| File | What it is |
|---|---|
| `apps/lab/client.py` | The HTTP client. Stdlib only. Names itself, mints idempotency keys, maps errors |
| `apps/lab/errors.py` | Failure by *who fixes it*: config (ours), account (the coach's), rejected (the visitor's), unavailable (nobody's) |
| `apps/lab/store.py` | The read layer. Returns `(data, notice)` and never raises at a template |
| `apps/lab/presenters.py` | A LAB service in the shape the Train templates already spoke |
| `apps/lab/intake.py` | The coach's form definition → Django fields → a `/leads` body |
| `apps/lab/catalogue.py` | Service specs, the gap questions, the brief, the reconcile |
| `apps/lab/management/commands/lab_catalogue.py` | The command that runs all of it |
| `catalogue/<coach>.json` | One file per coach: what the site offers |
| `scripts/seed_lab_dev.py` | The whole local setup, idempotent |

---

## 6. Traps

The first four are The LAB's own, from `docs/FINDTHE90_INTEGRATION.md` §7. The
rest were found building this.

1. **Name your client.** Cloudflare answers a default library User-Agent with an
   HTML 403, not JSON. `LAB_USER_AGENT` is sent on every request, and a non-JSON
   body is reported as *"check the User-Agent"* rather than a parse error.
2. **Idempotency keys must not be row ids.** Dev, staging and production all
   start at pk 1, so `lead-1` collides across them and the second environment
   records a success that never happened. UUIDs, minted per submission.
3. **An unknown `next` is a hand-off, not an error.** For the booking pass: send
   the visitor to The LAB to finish rather than guessing.
4. **`ExposeHeaders: ["ETag"]` on the R2 bucket.** For the film pass: without it
   each part PUT *succeeds* and the upload can never be completed.
5. **`.claude/settings.local.json` carries a `skip-worktree` bit** in the LAB
   checkout. `git status` shows it clean while `git merge` refuses to run. Clear
   it, merge, restore it:
   ```bash
   git update-index --no-skip-worktree .claude/settings.local.json
   ```
6. **`createcachetable` is not a migration** — see §3.
7. **Programmatic keys need explicit scopes** — see §2.
8. **Use the canonical host.** `thelabplatform.com` answers `301` to
   `www.thelabplatform.com` at Cloudflare. Following a cross-host redirect is
   where an `Authorization` header quietly goes missing, and a `POST` can arrive
   as a `GET`. `LAB_API_BASE` must be `https://www.thelabplatform.com`.
9. **macOS Python trusts nothing.** A python.org build ships an *empty* CA store
   until somebody runs `Install Certificates.command`, so every HTTPS call dies
   with `CERTIFICATE_VERIFY_FAILED` — which reads exactly like the platform being
   down. `apps/lab/client.py` resolves a bundle itself (certifi → Python's own
   store → `/etc/ssl/cert.pem` and friends → `SSL_CERT_FILE`) and reports this
   specific failure as a *config* error naming the fix. Verification is never
   disabled; an integration that silently stops checking certificates is worse
   than one that fails loudly.

## 6a. Live keys on a development box

A `lab_live_` key writes into the coach's **real** account — a real lead, a real
chat thread, a real email to them. Reads are always allowed. Writes are refused
unless `LAB_ALLOW_LIVE_WRITES=1`, and the refusal never reaches the network:

```
LabConfigError: This is a live key, so sending this would create a real lead in
the coach's account. Set LAB_ALLOW_LIVE_WRITES=1 to allow it deliberately, or
use a lab_test_ key while building.
```

The guard is on the key prefix rather than on `DEBUG`, because the thing that
makes a write dangerous is whose account it lands in, not which server sent it.
Test keys are unaffected — that is what they are for.

**A key pasted into a chat, an issue or a screenshot should be rotated.** The
coach does it themselves in Settings → API keys; nothing here needs changing but
the environment variable.

### The test suite must not be able to dial out

`apps/house` renders every room to check the chrome, which means an ordinary
`manage.py test` renders the Train room — and would have fired real requests at
a real coach's account using whatever sat in `.env`. It did, until this was
found: the suite took **20 seconds** instead of **0.3**, which is what a network
call in a unit test sounds like.

`config/settings.py` now blanks `LAB_API_BASE` and `LAB_API_KEY` whenever
`"test"` is in `sys.argv`, so every unmocked call fails instantly and locally.
Tests that exercise the client override the settings explicitly.

---

## 7. What is not built yet

In the order worth doing them.

| | Needs | Blocked by |
|---|---|---|
| Booking itself | `POST /bookings` → `next`, waiver, payment intent | Nothing. **Availability is already wired** — `store.next_open()` reads `GET /availability` for every service The LAB reports as `booking.mode = "calendar"` and the Train room prints real times. Taking one currently routes to an enquiry that names it |
| Payment | `/bookings/<id>/payment-intent`, Stripe Payment Element | Stripe test keys on both sides. No card data ever touches this server |
| Reviews | `GET /reviews` for the testimonials section | Nothing |
| Film / match analysis | `/gamefilm/*`, direct-to-R2 upload | R2 bucket + trap 4 |
| Camps | `GET /events`, hand off on `register_url` | Registration itself is a LAB gap (G5) |

### LAB-side gaps that constrain any wrapper

From `docs/FINDTHE90_INTEGRATION.md` §6. None block what is built; all of them
will shape what a second coach can sell.

- **G2** Discounts are whole dollars and unconditional. No percentages, no
  conditions. *Print them as prose; do not build a discount UI against `/price`.*
- **G3** No prepaid hour blocks. *Sell as an enquiry, not a checkout.*
- **G4** Camps have one price, not one that changes on a date.
- **G5** Camp registration is not on the API. *Hand off on `register_url`.*
- **G6** "Open" sessions have no request-and-admit flow.
- **G8** The platform has one timezone (`America/New_York`). Blocks the first
  coach outside Eastern, quietly and in the worst way.
- **G9** No product type for a non-session product.

---

## 8. Onboarding a second coach

The whole point of the exercise. Nothing in `apps/lab/` is Paul-specific.

1. The coach completes §2 in their own account and issues their own key
2. Set `LAB_API_BASE` and `LAB_API_KEY` in that site's environment
3. `GET /me` — confirm the name coming back is theirs
4. Restyle. The brand kit is the wrapper; the data is theirs

What does **not** transfer between coaches: nothing. There is no shared state,
no coach id in any request, and no way for one site's key to read another's
account. That is the property that makes handing a key to somebody else's
developer a reasonable thing to do.
