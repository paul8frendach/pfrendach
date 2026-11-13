"""Notification creation helpers."""

from __future__ import annotations

from django.contrib.auth.models import User
from django.conf import settings

from .models import Notification, Thread


def _coach_user():
    """Return the first superuser (Alex). None if none exists."""
    return User.objects.filter(is_superuser=True).order_by("pk").first()


def notify(user: User, *, kind: str, title: str, body: str = "", url: str = "",
           thread=None) -> Notification:
    return Notification.objects.create(
        user=user, kind=kind, title=title, body=body, url=url, thread=thread,
    )


def notify_coach_new_thread(thread: Thread) -> None:
    coach = _coach_user()
    if not coach:
        return
    notify(
        coach,
        kind=Notification.Kind.NEW_MESSAGE,
        title=f"New message from {thread.player.get_full_name() or thread.player.username}",
        body=thread.subject,
        url=f"/accounts/coach/inbox/{thread.reference}/",
        thread=thread,
    )


def notify_coach_escalation(thread: Thread) -> None:
    coach = _coach_user()
    if not coach:
        return
    notify(
        coach,
        kind=Notification.Kind.ESCALATION,
        title=f"Needs your reply — {thread.player.get_full_name() or thread.player.username}",
        body=thread.subject,
        url=f"/accounts/coach/inbox/{thread.reference}/",
        thread=thread,
    )


def notify_player_reply(thread: Thread) -> None:
    notify(
        thread.player,
        kind=Notification.Kind.REPLY,
        title="Alex replied to your message",
        body=thread.subject,
        url=f"/accounts/messages/{thread.reference}/",
        thread=thread,
    )
