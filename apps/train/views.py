from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from apps.house.mail import send_templated
from apps.house.models import Milestone, SiteConfig

from .forms import BookingForm
from .models import Booking, Law, SessionType, Slot


def index(request):
    return render(
        request,
        "train/index.html",
        {
            "laws": Law.objects.filter(is_live=True),
            "sessions": SessionType.objects.filter(is_live=True),
            "next_slots": Slot.objects.open().select_related("session_type")[:6],
            "milestones": Milestone.objects.filter(is_live=True, confirmed=True),
        },
    )


def session_detail(request, slug):
    session = get_object_or_404(SessionType, slug=slug, is_live=True)
    return render(
        request,
        "train/session_detail.html",
        {
            "session": session,
            "slots": Slot.objects.open().filter(session_type=session)[:20],
            "other_sessions": SessionType.objects.filter(is_live=True).exclude(pk=session.pk),
        },
    )


def schedule(request):
    """Everything open, grouped by day, for people who shop by time not by session."""
    slots = Slot.objects.open().select_related("session_type")[:60]
    days: dict = {}
    for slot in slots:
        days.setdefault(timezone.localtime(slot.starts_at).date(), []).append(slot)
    return render(
        request,
        "train/schedule.html",
        {
            "days": sorted(days.items()),
            "sessions": SessionType.objects.filter(is_live=True),
        },
    )


@require_http_methods(["GET", "POST"])
def book(request, slot_id):
    slot = get_object_or_404(
        Slot.objects.select_related("session_type"), pk=slot_id
    )
    if not slot.is_bookable:
        messages.error(request, "That slot is closed. Here is what is still open.")
        return redirect("train:schedule")

    if request.method == "POST":
        form = BookingForm(request.POST, slot=slot)
        if form.is_valid():
            # Lock the slot row so two submits cannot both take the last seat.
            with transaction.atomic():
                locked = Slot.objects.select_for_update().get(pk=slot.pk)
                if not locked.is_bookable:
                    messages.error(request, "That seat went while you were typing.")
                    return redirect("train:schedule")
                booking = form.save()
            _notify_booking(booking)
            return redirect("train:booking_detail", reference=booking.reference)
    else:
        form = BookingForm(slot=slot)

    return render(request, "train/book.html", {"slot": slot, "form": form})


def booking_detail(request, reference):
    booking = get_object_or_404(
        Booking.objects.select_related("slot", "slot__session_type"), reference=reference
    )
    return render(request, "train/booking_detail.html", {"booking": booking})


def _notify_booking(booking: Booking) -> None:
    site = SiteConfig.load()
    context = {"booking": booking, "slot": booking.slot, "site": site}
    send_templated(
        subject=f"Session request {booking.reference} — {booking.player_name}",
        template="booking_admin",
        context=context,
        to=[site.contact_email],
    )
    send_templated(
        subject=f"FRENDACH — request received ({booking.reference})",
        template="booking_player",
        context=context,
        to=[booking.email],
    )


# ------------------------------------------------------------------ JSON API
# Small, honest, read-mostly. It backs the booking UI and doubles as a worked
# example in the Build room.


def _session_payload(session: SessionType) -> dict:
    return {
        "slug": session.slug,
        "name": session.name,
        "format": session.get_format_display(),
        "summary": session.summary,
        "duration_minutes": session.duration_minutes,
        "capacity": session.capacity,
        "price": str(session.price) if session.price is not None else None,
        "price_label": session.price_label,
        "url": session.get_absolute_url(),
    }


def _slot_payload(slot: Slot) -> dict:
    local = timezone.localtime(slot.starts_at)
    return {
        "id": slot.pk,
        "session": slot.session_type.slug,
        "session_name": slot.session_type.name,
        "starts_at": slot.starts_at.isoformat(),
        "day": local.strftime("%A %-d %B"),
        "time": local.strftime("%-I:%M %p"),
        "location": slot.location,
        "seats_left": slot.seats_left,
        "book_url": f"/train/book/{slot.pk}/",
    }


@require_GET
def api_sessions(request):
    sessions = SessionType.objects.filter(is_live=True)
    return JsonResponse({"sessions": [_session_payload(s) for s in sessions]})


@require_GET
def api_slots(request):
    slots = Slot.objects.open().select_related("session_type")
    session_slug = request.GET.get("session")
    if session_slug:
        slots = slots.filter(session_type__slug=session_slug)
    try:
        limit = min(int(request.GET.get("limit", 40)), 200)
    except ValueError:
        limit = 40
    return JsonResponse({"slots": [_slot_payload(s) for s in slots[:limit]]})


@require_GET
def api_booking(request, reference):
    booking = Booking.objects.filter(reference=reference).select_related("slot").first()
    if booking is None:
        return JsonResponse({"error": "not found"}, status=404)
    return JsonResponse(
        {
            "reference": booking.reference,
            "status": booking.status,
            "status_label": booking.get_status_display(),
            "session": booking.slot.session_type.name,
            "starts_at": booking.slot.starts_at.isoformat(),
        }
    )
