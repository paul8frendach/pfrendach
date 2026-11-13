import logging
import os

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.house.mail import send_templated
from apps.house.models import SiteConfig

from . import payments
from .forms import CommissionForm
from .models import Commission, Method, Package, Payment, Photo, Work

logger = logging.getLogger(__name__)

# Where OMV commission requests are emailed. Its own inbox, not the house one.
OMV_NOTIFY_EMAIL = os.environ.get("OMV_NOTIFY_EMAIL", "paul@oasismediavisions.com")


def _grouped_work():
    """Live work bucketed by market category, newest first in each bucket."""
    live = Work.objects.filter(is_live=True)
    groups = []
    for value, label in Work.Category.choices:
        pieces = [w for w in live if w.category == value]
        if pieces:
            groups.append({"value": value, "label": label, "pieces": pieces})
    return groups


def index(request):
    category = request.GET.get("category")
    work = Work.objects.filter(is_live=True)
    if category in dict(Work.Category.choices):
        work = work.filter(category=category)
    featured = Work.objects.filter(is_live=True, is_featured=True)[:1].first()
    return render(
        request,
        "create/index.html",
        {
            "work": work,
            "featured": featured,
            "groups": _grouped_work(),
            "categories": Work.Category.choices,
            "active_category": category,
            "packages": Package.objects.filter(is_live=True),
            "methods": Method.objects.filter(is_live=True),
            "photos": list(Photo.objects.filter(is_live=True, is_featured=True)[:4])
            or list(Photo.objects.filter(is_live=True)[:4]),
            "photo_count": Photo.objects.filter(is_live=True).count(),
        },
    )


def photography(request):
    """The Photography sub-world — best stills grouped by style."""
    live = Photo.objects.filter(is_live=True)
    style = request.GET.get("style")
    if style in dict(Photo.Style.choices):
        live = live.filter(style=style)
    groups = []
    for value, label in Photo.Style.choices:
        shots = [p for p in live if p.style == value]
        if shots:
            groups.append({"value": value, "label": label, "photos": shots})
    return render(
        request,
        "create/photography.html",
        {
            "groups": groups,
            "styles": Photo.Style.choices,
            "active_style": style,
            "count": live.count(),
        },
    )


def work_detail(request, slug):
    piece = get_object_or_404(Work, slug=slug, is_live=True)
    return render(
        request,
        "create/work_detail.html",
        {
            "piece": piece,
            "more": Work.objects.filter(is_live=True, category=piece.category)
            .exclude(pk=piece.pk)[:3],
        },
    )


def request_film(request):
    """The professional service-request page. Pre-fills service / package from the URL."""
    service = request.GET.get("service")
    package = None
    package_slug = request.GET.get("package")
    if package_slug:
        package = Package.objects.filter(slug=package_slug, is_live=True).first()
        if package and not service:
            service = package.slug.split("-")[0]

    if request.method == "POST":
        form = CommissionForm(request.POST, service=service, package=package)
        if form.is_valid():
            commission = form.save(commit=False)
            commission.source_path = request.META.get("HTTP_REFERER", "")[:200]
            commission.save()
            site = SiteConfig.load()
            send_templated(
                subject=f"OMV commission — {commission.get_service_display()} · {commission.name}",
                template="commission_received",
                context={"commission": commission, "site": site},
                to=[OMV_NOTIFY_EMAIL],
            )
            messages.success(
                request,
                "Received. Paul reads every one of these himself — expect a real reply, not a robot.",
            )
            return redirect("create:request_thanks")
    else:
        form = CommissionForm(service=service, package=package)

    return render(
        request,
        "create/request.html",
        {
            "form": form,
            "packages": Package.objects.filter(is_live=True),
            "selected_package": package,
        },
    )


def request_thanks(request):
    return render(request, "create/request_thanks.html")


# ------------------------------------------------------------------ payments

@require_POST
def book(request):
    """Start a Stripe Checkout for a package deposit. Card entry is on Stripe."""
    package = get_object_or_404(Package, slug=request.POST.get("package"), is_live=True)
    if not package.bookable:
        messages.info(request, "That one is quote-first — tell me about your day and I'll send a booking link.")
        return redirect(f"{reverse('create:request')}?package={package.slug}")

    commission_id = request.POST.get("commission_id") or None
    payment = Payment.objects.create(
        package=package,
        commission_id=commission_id,
        kind=Payment.Kind.DEPOSIT,
        amount=package.deposit_amount,
        currency=os.environ.get("STRIPE_CURRENCY", "usd"),
        description=f"{package.name} — deposit to book",
        source_path=request.META.get("HTTP_REFERER", "")[:200],
    )
    try:
        session = payments.create_checkout_session(
            payment=payment,
            success_url=request.build_absolute_uri(reverse("create:book_success")) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.build_absolute_uri(reverse("create:book_cancel")),
            description=payment.description,
        )
    except Exception as exc:  # noqa: BLE001 — never 500 on a payment start
        logger.error("Stripe session create failed: %s", exc)
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status", "updated_at"])
        messages.error(request, "Couldn't reach checkout just now. Send a request and I'll get you a link.")
        return redirect(f"{reverse('create:request')}?package={package.slug}")

    payment.stripe_session_id = session.get("id", "")
    payment.checkout_url = session.get("url", "")
    payment.save(update_fields=["stripe_session_id", "checkout_url", "updated_at"])
    return redirect(session["url"])


def book_success(request):
    return render(request, "create/book_success.html")


def book_cancel(request):
    messages.info(request, "No charge made. Your date isn't held until a deposit goes through.")
    return redirect(f"{reverse('create:index')}#packages")


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Stripe's source of truth. Only this marks a Payment paid."""
    try:
        event = payments.verify_webhook(request.body, request.headers.get("Stripe-Signature", ""))
    except Exception as exc:  # noqa: BLE001 — bad signature or unparsable
        logger.warning("Stripe webhook rejected: %s", exc)
        return JsonResponse({"ok": False}, status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        payment = Payment.objects.filter(
            stripe_session_id=session.get("id", "")
        ).first() or Payment.objects.filter(
            pk=(session.get("metadata") or {}).get("payment_id") or 0
        ).first()
        if payment and payment.status != Payment.Status.PAID:
            details = session.get("customer_details") or {}
            payment.mark_paid(
                payment_intent=session.get("payment_intent", "") or "",
                name=details.get("name", "") or "",
                email=details.get("email", "") or "",
            )
            site = SiteConfig.load()
            send_templated(
                subject=f"OMV deposit paid — ${payment.amount} · {payment.customer_name or payment.customer_email}",
                template="payment_received",
                context={"payment": payment, "site": site},
                to=[OMV_NOTIFY_EMAIL],
            )
    return JsonResponse({"ok": True})
