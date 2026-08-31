"""Outbound notices. Console backend in dev, SMTP when EMAIL_LIVE is set."""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_templated(subject: str, template: str, context: dict, to: list[str]) -> int:
    """Render `template`.txt for a plain-text mail. Silent on failure by design —
    a dead SMTP host must never lose a booking that is already in the database."""
    body = render_to_string(f"mail/{template}.txt", context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=to,
    )
    return message.send(fail_silently=True)
