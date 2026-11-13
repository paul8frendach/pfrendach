"""
Accounts views: auth, player dashboard, messaging, coach dashboard.
"""

from __future__ import annotations

from django.contrib import messages as django_messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .ai import generate_response
from .forms import ComposeForm, OfferForm, PlayerRatingForm, ReplyForm, SignupForm
from .models import Message, Notification, Offer, PlayerProfile, Thread
from .notifications import (
    notify_coach_escalation,
    notify_coach_new_thread,
    notify_player_reply,
)


# ---------------------------------------------------------------- auth

def signup(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("accounts:dashboard")
    else:
        form = SignupForm()
    return render(request, "accounts/signup.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            next_url = request.GET.get("next") or "accounts:dashboard"
            return redirect(next_url)
    else:
        form = AuthenticationForm(request)
    return render(request, "accounts/login.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("house:home")


# ---------------------------------------------------------------- player dashboard

@login_required(login_url="/accounts/login/")
def dashboard(request):
    try:
        profile = request.user.profile
    except PlayerProfile.DoesNotExist:
        profile = PlayerProfile.objects.create(user=request.user)

    offers = [o for o in Offer.objects.filter(is_live=True)
              if o.is_visible_to(request.user)]
    threads = Thread.objects.filter(player=request.user).order_by("-updated_at")[:5]
    unread_notifs = Notification.objects.filter(user=request.user, is_read=False)

    return render(request, "accounts/dashboard.html", {
        "profile": profile,
        "offers": offers,
        "threads": threads,
        "unread_notifs": unread_notifs,
        "unread_count": unread_notifs.count(),
    })


# ---------------------------------------------------------------- messaging (player side)

@login_required(login_url="/accounts/login/")
def inbox(request):
    threads = Thread.objects.filter(player=request.user).order_by("-updated_at")
    return render(request, "accounts/inbox.html", {"threads": threads})


@login_required(login_url="/accounts/login/")
def compose(request):
    service_slug = request.GET.get("service", "")
    service_name = request.GET.get("service_name", "")
    initial = {}
    if service_name:
        initial["subject"] = f"Question about: {service_name}"
        initial["service"] = service_slug

    if request.method == "POST":
        form = ComposeForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                thread = Thread.objects.create(
                    player=request.user,
                    subject=form.cleaned_data["subject"],
                    service_slug=form.cleaned_data.get("service", ""),
                    service_name=service_name or form.cleaned_data.get("subject", ""),
                    status=Thread.Status.OPEN,
                    coach_unread=True,
                )
                player_msg = Message.objects.create(
                    thread=thread,
                    sender_type=Message.SenderType.PLAYER,
                    sender=request.user,
                    body=form.cleaned_data["body"],
                )
                # AI first response
                ai_reply = generate_response(
                    form.cleaned_data["body"],
                    service_name=thread.service_name,
                )
                ai_msg = Message.objects.create(
                    thread=thread,
                    sender_type=Message.SenderType.AI,
                    body=ai_reply.body,
                    is_ai_response=True,
                    is_escalation=ai_reply.should_escalate,
                    is_read_by_player=False,
                )
                if ai_reply.should_escalate:
                    thread.status = Thread.Status.ESCALATED
                    thread.save(update_fields=["status"])

            notify_coach_new_thread(thread)
            if ai_reply.should_escalate:
                notify_coach_escalation(thread)

            return redirect("accounts:thread", reference=thread.reference)
    else:
        form = ComposeForm(initial=initial)

    return render(request, "accounts/compose.html", {
        "form": form,
        "service_slug": service_slug,
        "service_name": service_name,
    })


@login_required(login_url="/accounts/login/")
def thread_view(request, reference):
    thread = get_object_or_404(Thread, reference=reference, player=request.user)
    thread.mark_player_read()

    # Mark AI messages as read too
    thread.messages.filter(is_read_by_player=False).update(is_read_by_player=True)

    # Mark related notifications read
    Notification.objects.filter(user=request.user, thread=thread, is_read=False).update(is_read=True)

    form = ReplyForm()
    if request.method == "POST":
        form = ReplyForm(request.POST)
        if form.is_valid():
            Message.objects.create(
                thread=thread,
                sender_type=Message.SenderType.PLAYER,
                sender=request.user,
                body=form.cleaned_data["body"],
            )
            thread.status = Thread.Status.OPEN
            thread.coach_unread = True
            thread.player_unread = False
            thread.save(update_fields=["status", "coach_unread", "player_unread", "updated_at"])
            notify_coach_new_thread(thread)
            return redirect("accounts:thread", reference=reference)

    msgs = thread.messages.order_by("created_at")
    return render(request, "accounts/thread.html", {
        "thread": thread, "msgs": msgs, "form": form,
    })


# ---------------------------------------------------------------- notifications API

@login_required(login_url="/accounts/login/")
def notif_count(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({"count": count})


@login_required(login_url="/accounts/login/")
@require_POST
def notif_mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.mark_read()
    return JsonResponse({"ok": True})


# ---------------------------------------------------------------- coach dashboard (staff only)

def _require_coach(view_fn):
    """Decorator: must be authenticated and is_staff."""
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return redirect("accounts:login")
        return view_fn(request, *args, **kwargs)
    wrapped.__name__ = view_fn.__name__
    return wrapped


@_require_coach
def coach_dashboard(request):
    profiles = PlayerProfile.objects.select_related("user").order_by("-rating", "user__last_name")
    offers   = Offer.objects.order_by("sort", "min_rating")
    threads  = Thread.objects.order_by("-updated_at")[:10]

    unread_threads = Thread.objects.filter(coach_unread=True).count()
    escalated      = Thread.objects.filter(status=Thread.Status.ESCALATED).count()

    # Simple analytics
    total_players = User.objects.filter(is_staff=False, is_superuser=False).count()
    rated_players = profiles.filter(rating__gt=0).count()

    return render(request, "accounts/coach_dashboard.html", {
        "profiles": profiles,
        "offers": offers,
        "recent_threads": threads,
        "unread_threads": unread_threads,
        "escalated": escalated,
        "total_players": total_players,
        "rated_players": rated_players,
    })


@_require_coach
def coach_players(request):
    profiles = PlayerProfile.objects.select_related("user").order_by("-rating", "user__last_name")
    return render(request, "accounts/coach_players.html", {"profiles": profiles})


@_require_coach
def coach_rate_player(request, pk):
    profile = get_object_or_404(PlayerProfile, pk=pk)
    if request.method == "POST":
        form = PlayerRatingForm(request.POST, instance=profile)
        if form.is_valid():
            p = form.save(commit=False)
            if "rating" in form.changed_data:
                p.rating_set_at = timezone.now()
            p.save()
            django_messages.success(
                request,
                f"{profile.display_name} updated — {profile.get_rating_display()}.",
            )
            return redirect("accounts:coach_players")
    else:
        form = PlayerRatingForm(instance=profile)
    return render(request, "accounts/coach_rate_player.html", {
        "profile": profile, "form": form,
    })


@_require_coach
def coach_offers(request):
    offers = Offer.objects.order_by("sort", "min_rating")
    return render(request, "accounts/coach_offers.html", {"offers": offers})


@_require_coach
def coach_offer_form(request, pk=None):
    offer = get_object_or_404(Offer, pk=pk) if pk else None
    if request.method == "POST":
        form = OfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            django_messages.success(request, "Offer saved.")
            return redirect("accounts:coach_offers")
    else:
        form = OfferForm(instance=offer)
    return render(request, "accounts/coach_offer_form.html", {
        "form": form, "offer": offer,
    })


@_require_coach
@require_POST
def coach_offer_toggle(request, pk):
    offer = get_object_or_404(Offer, pk=pk)
    offer.is_live = not offer.is_live
    offer.save(update_fields=["is_live"])
    return redirect("accounts:coach_offers")


# ---------------------------------------------------------------- coach inbox

@_require_coach
def coach_inbox(request):
    threads = (
        Thread.objects
        .select_related("player")
        .annotate(msg_count=Count("messages"))
        .order_by("-updated_at")
    )
    unread = threads.filter(coach_unread=True).count()
    escalated = threads.filter(status=Thread.Status.ESCALATED).count()
    return render(request, "accounts/coach_inbox.html", {
        "threads": threads,
        "unread": unread,
        "escalated": escalated,
    })


@_require_coach
def coach_thread(request, reference):
    thread = get_object_or_404(Thread, reference=reference)
    thread.mark_coach_read()
    thread.messages.filter(is_read_by_coach=False).update(is_read_by_coach=True)

    form = ReplyForm()
    if request.method == "POST":
        form = ReplyForm(request.POST)
        if form.is_valid():
            Message.objects.create(
                thread=thread,
                sender_type=Message.SenderType.COACH,
                sender=request.user,
                body=form.cleaned_data["body"],
                is_read_by_coach=True,
                is_read_by_player=False,
            )
            thread.status = Thread.Status.WAITING
            thread.player_unread = True
            thread.coach_unread = False
            thread.save(update_fields=["status", "player_unread", "coach_unread", "updated_at"])
            notify_player_reply(thread)
            return redirect("accounts:coach_thread", reference=reference)

    msgs = thread.messages.order_by("created_at")
    try:
        player_profile = thread.player.profile
    except PlayerProfile.DoesNotExist:
        player_profile = None

    return render(request, "accounts/coach_thread.html", {
        "thread": thread, "msgs": msgs, "form": form,
        "player_profile": player_profile,
    })
