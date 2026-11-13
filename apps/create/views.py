import logging
import os

from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
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
    # A real cinematic still fills the hero when there's no featured film yet.
    hero_photo = (
        Photo.objects.filter(is_live=True, style=Photo.Style.WEDDING).first()
        or Photo.objects.filter(is_live=True).first()
    )
    # Atmospheric side-angle frames the hero drifts through — the room feels
    # alive without pulling focus off the headline. Dark, cinematic picks only.
    _hero_slide_names = [
        "wedding-1.jpg", "aerial-2.jpg", "wedding-7.jpg",
        "sports-7.jpg", "wedding-3.jpg", "aerial-5.jpg",
    ]
    _have = set(
        Photo.objects.filter(is_live=True, image__in=_hero_slide_names)
        .values_list("image", flat=True)
    )
    hero_slides = [static(f"omv/gallery/{n}") for n in _hero_slide_names if n in _have]

    # Short, muted, looping teasers — a few seconds of the feeling, in motion.
    _teaser_set = [
        ("city", "Philadelphia, from the air"),
        ("staircase", "The first look"),
        ("reveal", "The reveal"),
        ("aerial", "Drone over the block"),
    ]
    teasers = [
        {"src": static(f"omv/teasers/{n}.mp4"),
         "poster": static(f"omv/teasers/{n}.jpg"), "label": label}
        for n, label in _teaser_set
    ]
    # Each film category borrows a real still of the nearest style, so the
    # "now booking" cards are never empty boxes.
    _style_for = {"wedding": "wedding", "event": "wedding", "school": "sports",
                  "listing": "aerial", "brand": "portrait", "stills": "portrait"}
    _by_style = {}
    cat_cards = []
    for value, label in Work.Category.choices:
        ps = _style_for.get(value, "wedding")
        if ps not in _by_style:
            _by_style[ps] = Photo.objects.filter(is_live=True, style=ps).first()
        p = _by_style[ps] or Photo.objects.filter(is_live=True).first()
        cat_cards.append({"value": value, "label": label,
                          "poster": static(p.static_path) if p else ""})
    return render(
        request,
        "create/index.html",
        {
            "work": work,
            "featured": featured,
            "hero_photo": hero_photo,
            "hero_slides": hero_slides,
            "teasers": teasers,
            "groups": _grouped_work(),
            "categories": Work.Category.choices,
            "cat_cards": cat_cards,
            "active_category": category,
            "packages": Package.objects.filter(is_live=True),
            "methods": Method.objects.filter(is_live=True),
            "photos": list(Photo.objects.filter(is_live=True, is_featured=True)[:4])
            or list(Photo.objects.filter(is_live=True)[:4]),
            "photo_count": Photo.objects.filter(is_live=True).count(),
            "omv_tab": "films",
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
            "omv_tab": "photography",
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

    authed = request.user.is_authenticated
    if request.method == "POST":
        form = CommissionForm(request.POST, service=service, package=package, authenticated=authed)
        if form.is_valid():
            commission = form.save(commit=False)
            commission.source_path = request.META.get("HTTP_REFERER", "")[:200]

            # The account is offered inside the quote, never as a wall before it.
            user = request.user if authed else None
            made_account = False
            if user is None and form.cleaned_data.get("create_account") and form.cleaned_data.get("password"):
                email = commission.email.strip()
                existing = (
                    User.objects.filter(username__iexact=email).first()
                    or User.objects.filter(email__iexact=email).first()
                )
                if existing:
                    messages.info(
                        request,
                        "You already have an account with that email — sign in and your request will be waiting.",
                    )
                else:
                    first = commission.name.strip().split(" ")[0][:150]
                    user = User.objects.create_user(
                        username=email[:150], email=email,
                        password=form.cleaned_data["password"], first_name=first,
                    )
                    auth_login(request, user)
                    made_account = True

            commission.client = user
            commission.save()

            site = SiteConfig.load()
            send_templated(
                subject=f"OMV commission — {commission.get_service_display()} · {commission.name}",
                template="commission_received",
                context={"commission": commission, "site": site},
                to=[OMV_NOTIFY_EMAIL],
            )
            if made_account:
                messages.success(
                    request,
                    f"Your account is set up and {commission.reference} is in front of Paul. "
                    "Track it right here — you'll see the quote and can pay your deposit when it lands.",
                )
                return redirect("create:account")
            if user:
                messages.success(request, f"Added to your projects — {commission.reference} is in front of Paul.")
                return redirect("create:account")
            messages.success(
                request,
                "Received. Paul reads every one of these himself — expect a real reply, not a robot.",
            )
            return redirect("create:request_thanks")
    else:
        form = CommissionForm(service=service, package=package, authenticated=authed)

    return render(
        request,
        "create/request.html",
        {
            "form": form,
            "packages": Package.objects.filter(is_live=True),
            "selected_package": package,
            "omv_tab": "request",
        },
    )


# ------------------------------------------------------------------ client portal

def signin(request):
    """OMV client sign-in. Lands them in their project portal."""
    if request.user.is_authenticated:
        return redirect("create:account")
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            dest = request.GET.get("next") or reverse("create:account")
            return redirect(dest)
    else:
        form = AuthenticationForm(request)
    return render(request, "create/signin.html", {"form": form, "omv_tab": "account"})


@require_POST
def signout(request):
    auth_logout(request)
    messages.info(request, "Signed out. Your projects are here whenever you come back.")
    return redirect("create:index")


@login_required(login_url="/create/signin/")
def account(request):
    """The client portal — every project, its status, and the deposit button."""
    commissions = list(request.user.omv_commissions.all())
    payments = (
        Payment.objects.filter(commission__client=request.user)
        .select_related("package", "commission")
        .order_by("-created_at")
    )
    return render(
        request,
        "create/account.html",
        {
            "commissions": commissions,
            "payments": payments,
            "open_count": sum(1 for c in commissions if c.is_open),
            "omv_tab": "account",
        },
    )


def request_thanks(request):
    return render(request, "create/request_thanks.html")


# ------------------------------------------------------------------ payments

@require_POST
def book(request):
    """Start a Stripe Checkout for a deposit. Card entry is on Stripe.

    Two ways in: a package pricecard on the site, or a quoted project in the
    client portal (which carries its own deposit and reference).
    """
    commission = None
    commission_id = request.POST.get("commission_id") or None
    if commission_id:
        commission = Commission.objects.filter(pk=commission_id).first()

    if commission is not None:
        if not commission.can_book_online:
            messages.info(request, "This one isn't ready to book online yet — Paul will send a link.")
            return redirect("create:account")
        package = commission.package
        amount = commission.booking_deposit
        description = f"Deposit to book — {commission.get_service_display()} · {commission.reference}"
        fallback = reverse("create:account")
    else:
        package = get_object_or_404(Package, slug=request.POST.get("package"), is_live=True)
        if not package.bookable:
            messages.info(request, "That one is quote-first — tell me about your day and I'll send a booking link.")
            return redirect(f"{reverse('create:request')}?package={package.slug}")
        amount = package.deposit_amount
        description = f"{package.name} — deposit to book"
        fallback = f"{reverse('create:request')}?package={package.slug}"

    payment = Payment.objects.create(
        package=package,
        commission=commission,
        kind=Payment.Kind.DEPOSIT,
        amount=amount,
        currency=os.environ.get("STRIPE_CURRENCY", "usd"),
        description=description,
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
        return redirect(fallback)

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
