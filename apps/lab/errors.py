"""What can go wrong between here and The LAB, named.

Every one of these carries a message written for whoever has to fix it. The
distinction that matters is not HTTP status but *who* fixes it: a
`LabConfigError` is Paul's, a `LabAccountError` is the coach's, and a
`LabUnavailable` is nobody's — it passes and the page should degrade rather
than break.
"""
from __future__ import annotations


class LabError(Exception):
    """Base. Never raised directly."""

    #: Shown to a visitor. Never contains a key, a URL or a stack.
    public_message = "Bookings are briefly unavailable. Please try again shortly."

    def __init__(self, message: str = "", *, code: str = "", status: int | None = None):
        super().__init__(message or self.__class__.__doc__ or "")
        self.code = code
        self.status = status


class LabConfigError(LabError):
    """The site is not wired up: no key, no base URL, or a key for the wrong account.

    Paul's to fix, and it should fail loudly in development rather than
    silently rendering an empty storefront.
    """


class LabAccountError(LabError):
    """The coach's LAB account cannot serve this request.

    A lapsed Pro subscription is the common one, and it is deliberately its own
    class: nothing in this codebase can fix it, and the operator needs to be
    told to go and renew rather than sent to read logs.
    """

    public_message = "This coach is not currently taking new enquiries online."


class LabRejected(LabError):
    """The LAB refused the submission, and the visitor can do something about it.

    The message is safe to show, because these are validation answers - a
    missing email, an address that already belongs to a LAB account.
    """

    def __init__(self, message: str = "", *, code: str = "", status: int | None = None):
        super().__init__(message, code=code, status=status)
        self.public_message = message or LabError.public_message


class LabUnavailable(LabError):
    """The LAB did not answer, or answered with something that is not ours.

    Timeouts, connection refused, 5xx, and Cloudflare's HTML 403 all land here.
    A read path should catch this and show what it has; a write path should
    tell the visitor to try again and keep what they typed.
    """
