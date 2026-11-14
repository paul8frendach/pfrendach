# PythonAnywhere Deploy Checklist — FindThe90

PA username: **pfrendach8**
Project root on PA: `/home/pfrendach8/findthe90/`
Settings module: `config.settings`
WSGI entry point: `config.wsgi.application`

---

## 1. Create virtualenv (first deploy only)

```bash
mkvirtualenv findthe90 --python=python3.12
workon findthe90
```

## 2. Pull / upload the code

```bash
cd /home/pfrendach8/
git clone <your-repo-url> findthe90
# — OR if the repo is already there —
cd /home/pfrendach8/findthe90/
git pull origin main
```

## 3. Install dependencies

```bash
workon findthe90
cd /home/pfrendach8/findthe90/
pip install -r requirements.txt
```

## 4. Create the .env file

```bash
cp /home/pfrendach8/findthe90/.env.example /home/pfrendach8/findthe90/.env
nano /home/pfrendach8/findthe90/.env
```

Fill in these values (everything else can stay as-is from the example):

```
DJANGO_SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(50))">
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=ft90.pfrendach.com,pfrendach8.pythonanywhere.com,findthe90.com,www.findthe90.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://ft90.pfrendach.com,https://findthe90.com,https://www.findthe90.com
SITE_DOMAIN=ft90.pfrendach.com
SITE_URL=https://ft90.pfrendach.com
TIME_ZONE=America/New_York

# Mail — set when you're ready to send real email
EMAIL_LIVE=0
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=<alex's email>
EMAIL_HOST_PASSWORD=<app password>
DEFAULT_FROM_EMAIL=hello@findthe90.com

# The LAB (Alex's coaching platform API key)
LAB_API_BASE=https://thelabplatform.com
LAB_API_KEY=<lab_live_... key from Alex's LAB account>
LAB_ALLOW_LIVE_WRITES=1

# Printful (from Printful dashboard → Settings → API)
PRINTFUL_API_KEY=<printful api key from Alex's account>
PRINTFUL_WEBHOOK_SECRET=<optional random string — register same value in Printful webhook settings>
PRINTFUL_CACHE_SECONDS=900
```

## 5. Run migrations

```bash
workon findthe90
cd /home/pfrendach8/findthe90/
python manage.py migrate
```

This creates all tables including the new shop app (`PrintfulProduct`, `PrintfulWebhookLog`).

## 6. Create superuser (first deploy only)

```bash
python manage.py createsuperuser
```

Use Alex's email as the username so he can log into /admin/.

## 7. Seed house data (optional but recommended)

```bash
python manage.py seed_house
```

This seeds the `SiteConfig` singleton and any house-level defaults.

## 8. Collect static files

```bash
python manage.py collectstatic --noinput
```

Static files land in `/home/pfrendach8/paulfrendach/staticfiles/`.

## 9. Configure the Web tab in PythonAnywhere

In the PA Web tab for your domain:

**Source code:** `/home/pfrendach8/findthe90`

**Working directory:** `/home/pfrendach8/findthe90`

**Virtualenv:** `/home/pfrendach8/.virtualenvs/findthe90`

**WSGI configuration file:** Edit the auto-generated WSGI file and replace its contents with:

```python
import os
import sys

path = '/home/pfrendach8/findthe90'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

## 10. Static and media file mappings

In the PA Web tab → Static files section, add:

| URL        | Directory                                               |
|------------|---------------------------------------------------------|
| `/static/` | `/home/pfrendach8/findthe90/staticfiles/`            |
| `/media/`  | `/home/pfrendach8/findthe90/media/`                  |

## 11. Register the Printful webhook (after first deploy)

Go to **developers.printful.com** → Webhooks (NOT the "Website" field in Store settings).

Add a new webhook:

```
URL: https://ft90.pfrendach.com/shop/printful/webhook/
Events: order_created, order_updated, order_failed, order_canceled, package_shipped, package_returned
```

If you set `PRINTFUL_WEBHOOK_SECRET` in .env, paste the same value into Printful's "Webhook secret" field.

## 12. Add products to the shop

1. Log into `/admin/` as superuser.
2. Go to **Shop → Printful products → Add**.
3. For each product you want on the site:
   - Enter the **Printful sync product ID** (find it in your Printful dashboard — it's the number in the product URL).
   - Set a **slug** (e.g. `ft90-training-tee`).
   - Optionally set a **display name** / **display description** to override the Printful copy.
   - Set **Is live = ✓** and a **sort** order.

## 13. Reload the web app

In the PA Web tab, click **Reload**.

Visit https://findthe90.com/shop/ to confirm the shop is live.

---

## DNS: pointing findthe90.com at PythonAnywhere

In your domain registrar, add:

```
Type: CNAME
Name: www
Value: pfrendach8.pythonanywhere.com

Type: CNAME  (or A → PA's IP if CNAME not allowed at apex)
Name: @
Value: pfrendach8.pythonanywhere.com
```

Then in the PA Web tab, add `findthe90.com` and `www.findthe90.com` as your domains and enable **Force HTTPS**.

---

## What Paul still needs to provide manually

- [ ] The Git remote URL (or upload the files manually)
- [ ] A generated `DJANGO_SECRET_KEY` (run `python -c "import secrets; print(secrets.token_urlsafe(50))"`)
- [ ] `PRINTFUL_API_KEY` — from Alex's Printful account, Settings → API
- [ ] `LAB_API_KEY` — from Alex's LAB account, Settings → API keys (use a live key for production)
- [ ] Email credentials (`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`) when ready to send real mail
- [ ] DNS records pointed at `pfrendach8.pythonanywhere.com`
- [ ] Printful sync product IDs added via /admin/ → Shop → Printful products
