"""Oasis link — a read-only summary of Oasis Media Visions for Paul's Oasis (oasis.pfrendach.com).

GET /oasis-link/ with `Authorization: Bearer <OASIS_LINK_SECRET>`.
- Read-only: it runs SELECTs and, where configured, a Stripe GET. It never writes.
- No fallback secret: unset means 503 for everyone.
- Counts, money and project references only — never a client's name, email, phone or address.

This is what lets Oasis oversee the OMV client pipeline end to end: enquiries waiting on a quote,
booked films still owed, and finished deliveries handed over in each client's portal folder.
"""
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

APP = "omv"


def _authorised(request):
    secret = getattr(settings, "OASIS_LINK_SECRET", "") or os.environ.get("OASIS_LINK_SECRET", "")
    if not secret:
        return None
    given = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    return hmac.compare_digest(given.encode(), secret.encode())


def stripe_summary(key, days=30):
    """Succeeded charges in the last `days`, straight from Stripe (GET only). Errors are reported, not hidden."""
    if not key:
        return {"configured": False}
    mode = "live" if "_live_" in key else "test"
    since = int(time.time()) - days * 86400
    out = {"configured": True, "mode": mode, "days": days, "charges": 0, "gross_cents": 0,
           "refunded_cents": 0, "failed": 0, "currency": None}
    url = "https://api.stripe.com/v1/charges?" + urllib.parse.urlencode({"limit": 100, "created[gte]": since})
    pages = 0
    while url and pages < 10:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}", "User-Agent": "oasis-link/1"})
        try:
            with urllib.request.urlopen(req, timeout=12) as r:
                data = json.load(r)
        except urllib.error.HTTPError as e:
            try:
                msg = json.load(e).get("error", {}).get("message", "")
            except Exception:
                msg = ""
            return {**out, "error": f"Stripe HTTP {e.code}: {msg[:160]}"}
        except Exception as e:
            return {**out, "error": f"Stripe unreachable: {type(e).__name__}"}
        for c in data.get("data", []):
            out["currency"] = out["currency"] or c.get("currency")
            if c.get("status") == "succeeded" and c.get("paid"):
                out["charges"] += 1
                out["gross_cents"] += c.get("amount", 0)
                out["refunded_cents"] += c.get("amount_refunded", 0)
            elif c.get("status") == "failed":
                out["failed"] += 1
        pages += 1
        if data.get("has_more") and data.get("data"):
            url = "https://api.stripe.com/v1/charges?" + urllib.parse.urlencode(
                {"limit": 100, "created[gte]": since, "starting_after": data["data"][-1]["id"]})
        else:
            url = None
    out["net_cents"] = out["gross_cents"] - out["refunded_cents"]
    return out


@never_cache
@require_GET
def view(request):
    ok = _authorised(request)
    if ok is None:
        return JsonResponse({"error": "OASIS_LINK_SECRET is not configured"}, status=503)
    if not ok:
        return JsonResponse({"error": "unauthorised"}, status=403)
    now = timezone.now()
    try:
        body = summary(now)
    except Exception as e:   # say what broke rather than 500 with a page
        return JsonResponse({"error": f"{type(e).__name__}: {e}"[:300]}, status=500)
    return JsonResponse({"app": APP, "generated_at": now.isoformat(), **body})


def summary(now):
    from django.db.models import Count, Q, Sum

    from apps.create.models import Commission, Deliverable, Payment

    S = Commission.Status
    d30 = now - timedelta(days=30)

    open_comms = Commission.objects.exclude(status=S.CLOSED)
    new_comms = Commission.objects.filter(status=S.NEW)              # on the site, not yet read/quoted
    quoted = Commission.objects.filter(status=S.QUOTED)
    booked = Commission.objects.filter(status=S.BOOKED)
    # Booked films still owed: a booked project with nothing marked ready in the client's folder yet.
    booked_owed = booked.annotate(
        ready=Count("deliverables", filter=Q(deliverables__is_ready=True))
    ).filter(ready=0).count()

    deliveries = Deliverable.objects.filter(is_ready=True)
    delivered_30d = deliveries.filter(delivered_at__gte=d30)
    clients_delivered = deliveries.values("commission_id").distinct().count()

    paid = Payment.objects.filter(status=Payment.Status.PAID)
    paid_30d = paid.filter(created_at__gte=d30)

    # Recent activity, as plain timeline updates (good news, not fires) — references only, no client PII.
    recent = []
    for d in deliveries.select_related("commission").order_by("-delivered_at")[:6]:
        ref = d.commission.reference if d.commission_id else "—"
        recent.append({"kind": "delivery", "at": (d.delivered_at or d.created_at).isoformat(),
                       "title": f"Delivered · {d.get_kind_display()} · {d.title[:50]} → {ref}"})
    for c in new_comms.order_by("-created_at")[:6]:
        recent.append({"kind": "enquiry", "at": c.created_at.isoformat(),
                       "title": f"New enquiry · {c.get_service_display()} · {c.location or 'MD'} · {c.reference}"})
    recent.sort(key=lambda r: r["at"], reverse=True)

    return {
        "metrics": {
            "commissions_open": open_comms.count(),
            "commissions_new": new_comms.count(),
            "quotes_open": quoted.count(),
            "quotes_open_value": float(quoted.aggregate(s=Sum("quote_amount"))["s"] or 0),
            "booked_active": booked.count(),
            "deliveries_owed": booked_owed,                # booked films with nothing delivered yet
            "deliveries_ready": deliveries.count(),        # finished items live in client folders
            "deliveries_30d": delivered_30d.count(),
            "clients_with_deliveries": clients_delivered,
            "payments_paid_30d": paid_30d.count(),
            "payments_paid_30d_value": float(paid_30d.aggregate(s=Sum("amount"))["s"] or 0),
        },
        "stripe": stripe_summary(getattr(settings, "STRIPE_SECRET_KEY", "")),
        "recent": recent[:10],
    }
