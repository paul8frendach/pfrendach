"""A thin, honest client for The LAB's public API.

WHY STDLIB
    This site ships six dependencies. The API is a handful of JSON endpoints
    behind a bearer token, which `urllib` covers without adding a seventh.

WHAT THIS DELIBERATELY DOES NOT DO
    It never computes a price. `GET /services` returns what a session costs at
    the cheapest and dearest combination this coach allows, and `GET /price`
    answers for a specific one; multiplying a rate here would produce a number
    the coach's own checkout then contradicts. The storefront prints what it is
    given.

    It never names a coach. There is no coach parameter anywhere in the API -
    the key IS the account - so a bug here cannot reach another coach's data.
"""
from __future__ import annotations

import json
import logging
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
import uuid
from functools import lru_cache
from typing import Any

from django.conf import settings
from django.core.cache import cache

from .errors import (LabAccountError, LabConfigError, LabError, LabRejected,
                     LabUnavailable)

logger = logging.getLogger(__name__)

# Errors the coach or the operator must resolve, not the visitor and not us.
_ACCOUNT_CODES = {"subscription_required", "no_intake_form"}
# Errors that mean this site is wired up wrong.
_CONFIG_CODES = {"missing_key", "invalid_key", "missing_scope"}


def _setting(name: str, default: Any = None) -> Any:
    return getattr(settings, name, default)


# Where a CA bundle might live when Python's own trust store is empty. This is
# the macOS case: a python.org build ships no certificates until somebody runs
# `Install Certificates.command`, so `ssl.create_default_context()` trusts
# nothing and EVERY https call fails with "unable to get local issuer
# certificate" — which reads like the far end is broken.
_CA_BUNDLES = (
    "/etc/ssl/cert.pem",                          # macOS
    "/opt/homebrew/etc/ca-certificates/cert.pem",  # Homebrew, Apple silicon
    "/usr/local/etc/ca-certificates/cert.pem",     # Homebrew, Intel
    "/etc/pki/tls/certs/ca-bundle.crt",            # RHEL / Fedora
    "/etc/ssl/certs/ca-certificates.crt",          # Debian / Ubuntu
)


@lru_cache(maxsize=1)
def _ssl_context() -> ssl.SSLContext | None:
    """A context that actually verifies, or None to let urllib decide.

    Order matters: `certifi` when installed, then Python's own store if it has
    anything in it (the normal Linux case, and what production uses), then a
    known system bundle. Verification is never turned off — an integration that
    silently stops checking certificates is worse than one that fails loudly,
    because the failure is the only thing that would ever tell you.
    """
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass

    context = ssl.create_default_context()
    if context.get_ca_certs():
        return context

    override = os.environ.get("SSL_CERT_FILE")
    for path in ((override,) if override else ()) + _CA_BUNDLES:
        if path and os.path.exists(path):
            try:
                return ssl.create_default_context(cafile=path)
            except (ssl.SSLError, OSError):
                continue
    return None


class LabClient:
    """One coach's LAB account, reachable over HTTP.

    Construct with no arguments to use the configured site key. Pass `base` and
    `key` explicitly in tests, or to talk to a second coach's account.
    """

    def __init__(self, base: str | None = None, key: str | None = None,
                 *, timeout: float | None = None):
        self.base = (base if base is not None else _setting("LAB_API_BASE", "")).rstrip("/")
        self.key = key if key is not None else _setting("LAB_API_KEY", "")
        self.timeout = timeout if timeout is not None else float(_setting("LAB_TIMEOUT", 10))
        # Trap #1 from the LAB's own integration notes: a default library
        # User-Agent gets an HTML 403 from Cloudflare, not our JSON, and a
        # client that reads every error as "The LAB is down" shows nothing
        # wrong at all. Name ourselves.
        self.user_agent = _setting("LAB_USER_AGENT", "paulfrendach.com/1.0")

    # ------------------------------------------------------------ plumbing

    @property
    def is_configured(self) -> bool:
        return bool(self.base and self.key)

    def _require_config(self) -> None:
        if not self.is_configured:
            raise LabConfigError(
                "LAB_API_BASE and LAB_API_KEY must both be set. Run "
                "scripts/seed_lab_dev.py against a local LAB, or paste a key "
                "from Settings -> API keys.",
                code="not_configured",
            )

    def _request(self, method: str, path: str, *, params: dict | None = None,
                 body: dict | None = None, idempotency_key: str | None = None) -> Any:
        self._require_config()
        url = f"{self.base}/api/v1/{path.lstrip('/')}"
        if params:
            clean = {k: v for k, v in params.items() if v not in (None, "")}
            if clean:
                url = f"{url}?{urllib.parse.urlencode(clean)}"

        data = json.dumps(body).encode() if body is not None else None
        headers = {
            "Authorization": f"Bearer {self.key}",
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }
        if data is not None:
            headers["Content-Type"] = "application/json"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        kwargs = {"timeout": self.timeout}
        if url.startswith("https://"):
            context = _ssl_context()
            if context is not None:
                kwargs["context"] = context
        try:
            with urllib.request.urlopen(request, **kwargs) as response:
                return self._decode(response.read(), response.status)
        except urllib.error.HTTPError as exc:
            raise self._from_http_error(exc) from exc
        except urllib.error.URLError as exc:
            # Connection refused, DNS, TLS, timeout. The LAB being down must
            # not take this site down with it.
            reason = str(exc.reason)
            if "CERTIFICATE_VERIFY_FAILED" in reason:
                # Almost always a machine with no CA bundle rather than a real
                # certificate problem, and saying so saves an afternoon.
                raise LabConfigError(
                    f"TLS verification failed reaching {self.base}. This box has "
                    "no CA bundle Python can see - install certifi, or run "
                    "Python's Install Certificates.command, or set SSL_CERT_FILE. "
                    f"({reason})",
                    code="no_ca_bundle") from exc
            raise LabUnavailable(f"Could not reach The LAB at {self.base}: {reason}",
                                 code="unreachable") from exc

    @staticmethod
    def _decode(raw: bytes, status: int) -> Any:
        try:
            return json.loads(raw.decode() or "{}")
        except (ValueError, UnicodeDecodeError) as exc:
            # HTML where JSON belongs is the Cloudflare-403 shape, and it is
            # worth naming rather than reporting as a parse failure.
            raise LabUnavailable(
                f"The LAB returned {status} with a non-JSON body "
                f"({raw[:80]!r}). If this is production, check the User-Agent.",
                code="bad_response", status=status,
            ) from exc

    @staticmethod
    def _from_http_error(exc: urllib.error.HTTPError) -> LabError:
        status = exc.code
        try:
            payload = json.loads(exc.read().decode() or "{}")
        except (ValueError, UnicodeDecodeError):
            payload = {}
        detail = payload.get("error") or {}
        code = detail.get("code", "")
        message = detail.get("message") or f"The LAB answered {status}."

        if code in _ACCOUNT_CODES:
            return LabAccountError(message, code=code, status=status)
        if code in _CONFIG_CODES:
            return LabConfigError(message, code=code, status=status)
        if status == 429:
            return LabUnavailable(message, code=code or "rate_limited", status=status)
        if status >= 500:
            return LabUnavailable(message, code=code or "server_error", status=status)
        # 400/404/409 that the caller or the visitor can act on.
        return LabRejected(message, code=code, status=status)

    # ------------------------------------------------------------ verbs

    def get(self, path: str, *, params: dict | None = None, cache_for: int | None = None) -> Any:
        """A read, optionally cached.

        Services and the intake form are read on nearly every page view and
        change when the coach edits them, which is rarely. Caching them keeps a
        storefront render to zero upstream calls without going stale for longer
        than the coach would notice.
        """
        if not cache_for:
            return self._request("GET", path, params=params)

        token = urllib.parse.urlencode(sorted((params or {}).items()))
        # The key is in the cache key so rotating it cannot serve another
        # account's cached answer.
        key = f"lab:{self.base}:{self.key[-8:]}:{path}:{token}"
        hit = cache.get(key)
        if hit is not None:
            return hit
        value = self._request("GET", path, params=params)
        cache.set(key, value, cache_for)
        return value

    @property
    def is_live(self) -> bool:
        return self.key.startswith("lab_live_")

    def _guard_write(self) -> None:
        """Refuse a live write that nobody asked for.

        A `lab_live_` key writes into the coach's real account — a real lead, a
        real chat thread, a real email to them. That is correct in production
        and wrong on a laptop, and the difference is a single environment
        variable rather than a different key, so the guard is here rather than
        left to whoever is running the server.
        """
        if self.is_live and not _setting("LAB_ALLOW_LIVE_WRITES", False):
            raise LabConfigError(
                "This is a live key, so sending this would create a real lead "
                "in the coach's account. Set LAB_ALLOW_LIVE_WRITES=1 to allow "
                "it deliberately, or use a lab_test_ key while building.",
                code="live_write_not_armed",
            )

    def post(self, path: str, body: dict, *, idempotency_key: str | None = None) -> Any:
        """A write. Always idempotent.

        Trap #2: idempotency keys must not be row ids. Dev, staging and
        production all start at pk 1, so `lead-1` collides across them and the
        second environment records a success that never happened. A UUID is
        minted here when the caller does not supply one.
        """
        self._guard_write()
        return self._request("POST", path, body=body,
                             idempotency_key=idempotency_key or str(uuid.uuid4()))

    # ------------------------------------------------------------ endpoints

    def me(self) -> dict:
        """Who this key belongs to. Cheap, and the first thing to check when
        leads go missing: a key pointed at the wrong account looks like
        nothing at all until somebody asks where their enquiries went."""
        return self.get("me")

    def intake_form(self, *, cache_for: int | None = None) -> dict:
        """The coach's live intake configuration.

        A question the coach adds in The LAB appears on this site with no
        deploy. That is the whole reason the form is rendered from here rather
        than hand-built.
        """
        return self.get("intake-form", cache_for=cache_for)

    def services(self, *, cache_for: int | None = None) -> list[dict]:
        return (self.get("services", cache_for=cache_for) or {}).get("services", [])

    def availability(self, service_id: int, *, cache_for: int | None = None) -> dict:
        """Real bookable times for one service.

        Needs `signup:write`, and answers only for a service The LAB reports as
        `booking.mode == "calendar"` — anything else has no location or no
        packages and there is nothing to offer.
        """
        return self.get("availability", params={"service": service_id},
                        cache_for=cache_for)

    def blocks(self, *, cache_for: int | None = None) -> list[dict]:
        """Prepaid blocks: N sessions bought up front.

        The saving against buying singly arrives already worked out. Do not
        recompute it — what a single session costs depends on the coach's
        packages and floors, and a site that multiplies will contradict the
        card next to it.
        """
        return (self.get("blocks", cache_for=cache_for) or {}).get("blocks", [])

    def write_block(self, payload: dict, *, idempotency_key: str | None = None) -> dict:
        """Create or update one prepaid block. Needs `services:write`.

        The block names its service by the caller's own `external_ref`, so a
        service and its blocks can be provisioned in one pass without waiting
        to learn what id The LAB allocated.
        """
        return self.post("blocks/write", payload, idempotency_key=idempotency_key)

    def create_lead(self, payload: dict, *, idempotency_key: str | None = None) -> dict:
        return self.post("leads", payload, idempotency_key=idempotency_key)

    def write_service(self, payload: dict, *, idempotency_key: str | None = None) -> dict:
        """Create or update one service, keyed on its `external_ref`.

        Needs `services:write`, which keys issued before that scope existed do
        not carry — they keep working exactly as issued, and a 403 here means
        the coach should reissue rather than that anything is broken.

        Raises `LabRejected` with code `coach_edited` when the coach has changed
        that service in The LAB since the last write. That is not a failure: it
        is the coach winning, which is the design. Show them what differs before
        deciding whether to resend with `force`.
        """
        return self.post("services/write", payload, idempotency_key=idempotency_key)


def client() -> LabClient:
    """The site's own client, for view code that does not need a custom one."""
    return LabClient()
