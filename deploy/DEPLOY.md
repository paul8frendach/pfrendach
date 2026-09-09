# Deploying paulfrendach.com to `pfrendach.com`

Written to be followed in order. Steps 1–6 get the site live on the
`*.pythonanywhere.com` address; 7–9 attach `pfrendach.com` itself.

The account username is `pfrendach8` throughout.

**This site is the apex.** `pfrendach.com` is Paul's own domain and this is
Paul's own portfolio, so it takes the root. Client previews keep the pattern in
`~/findthe90/deploy/PREVIEW-DOMAIN.md`: one subdomain each, `ft90.pfrendach.com`
and so on. Nothing here changes that.

---

## 0. Before you start — the two things only you can check

**Does your PythonAnywhere plan have a web app slot free?** The account already
runs `findthe90`, `sunset-landing` and `debrief`. A plan that is full will let
you do everything below and then refuse at the Web tab, which is a bad moment to
find out. Web tab → the "Add a new web app" button says so.

**`pfrendach.com` resolves nowhere right now.** It is registered at Cloudflare
(created 2026-09-07) but the apex has no record. `ft90.pfrendach.com` already
points at PythonAnywhere, so the zone is live and working — it is only the root
that is empty. Step 8 fills it.

---

## 1. Get the code onto the box

There is no git remote for this project, so the bundle is the delivery.

On the Mac:

```bash
cd ~/Desktop/paulfrendach && bash deploy/make-bundle.sh
```

That writes `~/Desktop/paulfrendach-deploy.tar.gz` and **refuses to build if
`.env` ended up inside it** — that file holds a live LAB key, and a bundle
carrying it becomes a working credential sitting in a Downloads folder.

Upload it through the PythonAnywhere **Files** tab, then in a **Bash console**:

```bash
cd ~ && tar -xzf paulfrendach-deploy.tar.gz
```

## 2. Bootstrap

```bash
bash ~/paulfrendach/deploy/bootstrap.sh
```

It makes a Python 3.12 virtualenv (Django 6.0 needs 3.12+), installs
requirements, migrates, collects static, and seeds the house.

**`seed_house` is not optional.** The three tabs in the chrome — Create, Build,
Train — are database rows. Without it every page renders with an empty nav and
looks broken in a way that reads like a CSS fault.

## 3. Fill in `.env`

`bootstrap.sh` copies `deploy/env.production.example` to `.env` and leaves two
placeholders. Both must be replaced or the app will not start:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"   # DJANGO_SECRET_KEY
```

`LAB_API_KEY` is Paul's own key from thelabplatform.com → Settings → API keys.

Note `LAB_ALLOW_LIVE_WRITES=true` in that file. It is deliberate and it belongs
only here: the guard exists to stop a laptop writing into a real coach's
account, and production is the case it was built to allow. With it false the
enquiry form renders and then refuses to send, which is worse than having no
form at all.

## 4. Web tab

| | |
|---|---|
| Source code | `/home/pfrendach8/paulfrendach` |
| Working directory | `/home/pfrendach8/paulfrendach` |
| Virtualenv | `/home/pfrendach8/.virtualenvs/paulfrendach` |

**WSGI configuration file** → replace *everything* in it with the contents of
`~/paulfrendach/deploy/pythonanywhere_wsgi.py`. The default template does not
load `.env`, and settings read `os.environ` at import — so a `.env` loaded
afterwards has no effect and the site runs on development defaults with DEBUG
on. That would print the LAB key into the browser on the first error.

**Static files:**

| URL | Directory |
|---|---|
| `/static/` | `/home/pfrendach8/paulfrendach/staticfiles` |
| `/media/` | `/home/pfrendach8/paulfrendach/media` |

## 5. Reload, and look at it

Press **Reload**, then open `https://pfrendach8.pythonanywhere.com`.

Check all three rooms render and the tab rail has three tabs. If the nav is
empty, step 2's seed did not run.

## 6. What will look wrong, and is not

**`/train/enquire/` says the enquiry form is closed.** That is correct and it is
not a bug in this site: Paul's LAB intake form has `is_enabled: false`. The
wrapper reads that and says so rather than showing a form that collects nothing.
Turn it on in The LAB (page settings → the CTA panel) and the form appears on
the next page load, no deploy.

**No prepaid blocks on the Train tab.** `GET /api/v1/blocks` only exists on
The LAB's `staging` branch, which is not deployed. The client degrades quietly
rather than showing a broken section.

---

## 7. Get the CNAME target

Web tab → the domain field. Once you set a custom domain PythonAnywhere shows
the `webapp-NNNNNNN.pythonanywhere.com` hostname to point at. It is **per web
app** — `ft90` uses `webapp-3205318`, and this one will be a different number.
Do not reuse ft90's.

## 8. Cloudflare DNS

Two records, both **DNS only** (grey cloud, not orange):

| Type | Name | Target | Proxy |
|---|---|---|---|
| CNAME | `@` | `webapp-NNNNNNN.pythonanywhere.com` | **DNS only** |
| CNAME | `www` | `webapp-NNNNNNN.pythonanywhere.com` | **DNS only** |

A CNAME on the apex is not ordinary DNS; Cloudflare flattens it to A records
automatically, which is why this works here and would not at most registrars.

**The grey cloud matters.** Proxying breaks PythonAnywhere's Let's Encrypt
HTTP-01 challenge — Cloudflare answers the challenge instead of PA, and the
certificate request fails in a way that is genuinely hard to read.

## 9. HTTPS

Once the record resolves (`dig +short pfrendach.com`), Web tab → **HTTPS
certificate → Auto-renewing Let's Encrypt**.

Then set `DJANGO_ALLOWED_HOSTS` to include the apex if you have not already, and
reload.

---

## HSTS — raise it slowly

`config/settings.py` sets `SECURE_HSTS_INCLUDE_SUBDOMAINS` and
`SECURE_HSTS_PRELOAD`. On the apex, `includeSubDomains` reaches
`ft90.pfrendach.com` and **every preview subdomain you create later**.

`env.production.example` therefore starts `SECURE_HSTS_SECONDS=300`. Five
minutes is recoverable; the settings default of a year is not — a browser that
saw the header keeps enforcing it whatever you do at your end, and a future
client subdomain that is not on HTTPS yet would simply refuse to load.

Raise it to `31536000` once the apex has served HTTPS happily for a few days
and you are content that every subdomain will always be HTTPS.

---

## Redeploying, later

```bash
cd ~/Desktop/paulfrendach && bash deploy/make-bundle.sh     # on the Mac
# upload, then on the server:
cd ~ && tar -xzf paulfrendach-deploy.tar.gz && bash ~/paulfrendach/deploy/update.sh
```

`update.sh` backs the database up, migrates, re-collects static and touches the
right WSGI file to reload — matched by **content**, not by name, so it cannot
reload findthe90 or debrief by accident.
