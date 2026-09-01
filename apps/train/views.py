import uuid

from django.contrib import messages
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from apps.house.mail import send_templated
from apps.house.models import Milestone, SiteConfig
from apps.lab import store
from apps.lab.errors import LabError, LabRejected
from apps.lab.intake import MAX_ATHLETES, build_form_class, payload_from

from .forms import BookingForm
from .models import Booking, Law, SessionType, Slot


def index(request):
    """The Train room. The tariff is The LAB's answer, not ours.

    `services` are the coach's own, priced by their account. When The LAB
    cannot be reached `notice` carries a sentence to print in place of the
    list — never a cached-from-somewhere-else price.
    """
    services, notice = store.storefront()
    # Real times, from the coach's own calendar. The local Slot rows are not a
    # fallback here: a page whose prices are live and whose times are invented
    # is worse than one that says there is nothing open, because only one half
    # of it looks wrong.
    slots, _ = store.next_open(limit=3)
    blocks, _ = store.prepaid_blocks()
    return render(
        request,
        "train/index.html",
        {
            "laws": Law.objects.filter(is_live=True),
            "services": services,
            "services_notice": notice,
            "next_slots": slots,
            "blocks": blocks,
            "milestones": Milestone.objects.filter(is_live=True, confirmed=True),
        },
    )


def service_detail(request, service_id):
    """One LAB service. 404 only when The LAB answered and did not have it —
    an outage shows the room with a notice rather than pretending it is gone."""
    card, notice = store.find_service(service_id)
    if card is None and notice is None:
        raise Http404("No such service")
    others = [c for c in store.storefront()[0] if c.id != service_id]
    return render(
        request,
        "train/service_detail.html",
        {"service": card, "services_notice": notice, "other_services": others},
    )


@require_http_methods(["GET", "POST"])
def enquire(request):
    """The coach's own intake form, rendered here and posted to their account.

    The form is not written in this repo. `GET /api/v1/intake-form` says what
    to ask; a question Paul adds in The LAB appears here on the next page load.
    """
    definition, notice = store.intake_definition()
    if definition is None:
        return render(request, "train/enquire.html",
                      {"form": None, "notice": notice, "service": None})

    service = None
    try:
        wanted = int(request.GET.get("service") or request.POST.get("service") or 0)
    except (TypeError, ValueError):
        wanted = 0
    if wanted:
        service, _ = store.find_service(wanted)

    try:
        athletes = int(request.POST.get("athlete_count")
                       or request.GET.get("athletes") or 1)
    except (TypeError, ValueError):
        athletes = 1
    athletes = max(1, min(athletes, MAX_ATHLETES))

    # "Add another player" is a submit button, not script. It re-renders with
    # one more block and keeps what has been typed, so the control works with
    # JavaScript off — and the extra block is built from the coach's own
    # configuration rather than cloned in the browser from a stale copy.
    if request.method == "POST" and "add_athlete" in request.POST:
        athletes = min(athletes + 1, MAX_ATHLETES)
        form_class = build_form_class(definition, athletes=athletes)
        # Unbound with `initial`, not bound: they asked for another row, not
        # for the form to be marked wrong everywhere they had not reached yet.
        form = form_class(initial=_posted_initial(request.POST, athletes))
        return render(request, "train/enquire.html", {
            "form": form, "definition": definition, "service": service,
            "athlete_count": athletes, "max_athletes": MAX_ATHLETES,
            "notice": None,
        })

    form_class = build_form_class(definition, athletes=athletes)

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            payload = payload_from(form.cleaned_data, definition, athletes=athletes)
            if service is not None:
                # Which card they came from is the first thing the coach wants
                # to know, and the API has nowhere structured to put it.
                payload["notes"] = "\n\n".join(
                    part for part in [payload.get("notes", ""),
                                      f"Enquiring about: {service.name}"] if part
                )
            # Trap: an idempotency key must not be a row id. Dev, staging and
            # production all start at pk 1. Minted per submission and held in
            # the session so a double-submit replays rather than duplicates.
            session_key = f"lab_idem_{request.session.session_key or 'anon'}"
            idem = request.session.get(session_key) or str(uuid.uuid4())
            request.session[session_key] = idem
            try:
                result = store.submit_lead(payload, idempotency_key=idem)
            except LabRejected as exc:
                # Something the visitor can act on — a duplicate address, a
                # missing field. Their typing is still in `form`.
                form.add_error(None, exc.public_message)
            except LabError as exc:
                form.add_error(None, exc.public_message)
            else:
                request.session.pop(session_key, None)
                request.session["lab_lead_id"] = result.get("lead_id")
                return redirect("train:enquiry_sent")
    else:
        form = form_class(initial={"athlete_count": athletes})

    return render(request, "train/enquire.html", {
        "form": form,
        "definition": definition,
        "service": service,
        "athlete_count": athletes,
        "max_athletes": MAX_ATHLETES,
        "notice": None,
    })


def _posted_initial(post, athletes: int) -> dict:
    """What was typed, as `initial` for a rebuilt form.

    getlist, because a checkboxes question posts one name many times and
    `.dict()` would keep only the last box ticked.
    """
    initial = {}
    for key in post:
        if key in ("csrfmiddlewaretoken", "add_athlete"):
            continue
        values = post.getlist(key)
        initial[key] = values if len(values) > 1 else values[0]
    initial["athlete_count"] = athletes
    return initial


def enquiry_sent(request):
    return render(request, "train/enquiry_sent.html",
                  {"lead_id": request.session.get("lab_lead_id")})


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
    """Everything open, grouped by day, for people who shop by time not by session.

    Grouped on the coach's own day label rather than on a parsed datetime: The
    LAB already answered in their local zone, and re-deriving the date here in
    the server's zone is how a Thursday evening session lands on Friday.
    """
    slots, notice = store.next_open(limit=40)
    days: list = []
    for slot in slots:
        if days and days[-1][0] == slot.day_label:
            days[-1][1].append(slot)
        else:
            days.append((slot.day_label, [slot]))
    services, services_notice = store.storefront()
    return render(
        request,
        "train/schedule.html",
        {
            "days": days,
            "notice": notice or services_notice,
            "services": services,
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
