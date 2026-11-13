"""
AI first-responder stub.

This is the layer between a player's message and Alex. When a player sends a
message, the AI responds first with a canned or context-aware reply. If the
message matches a known pattern (pricing, booking, schedule) it gives a useful
answer. If it cannot handle it, it escalates to Alex.

STUB PHASE: responses are rule-based string matches. Replace the body of
`generate_response()` with a real LLM call when the model is trained on
Alex's services.
"""

from __future__ import annotations

import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)

# Keyword patterns → canned response. Order matters: first match wins.
_RULES: list[tuple[list[str], str, bool]] = [
    # (keywords, response, escalate)
    (
        ["price", "cost", "how much", "fee", "rate"],
        "Session prices depend on the format and whether it's 1-on-1 or a group. "
        "The current rates are listed on the training page. To get an exact quote "
        "for your situation, I'll make sure Alex follows up with you directly.",
        True,
    ),
    (
        ["book", "schedule", "slot", "available", "time", "when"],
        "Open slots are listed on the schedule page at /train/schedule/. "
        "You can tap any slot to send a booking request — Alex confirms each one "
        "by hand, usually within 24 hours.",
        False,
    ),
    (
        ["film", "video", "footage", "analysis"],
        "Film sessions are available — Alex breaks down match footage and "
        "identifies specific areas to work on. You can enquire at /train/enquire/. "
        "If you have footage ready, mention it in the notes.",
        False,
    ),
    (
        ["group", "team", "club"],
        "Group and team sessions are available. The size and format depend on "
        "what you need — I'll flag this for Alex so he can reach out with details.",
        True,
    ),
    (
        ["cancel", "reschedule", "change"],
        "I'll flag your request for Alex — he handles rescheduling personally "
        "so he can find a time that works.",
        True,
    ),
]

_FALLBACK = (
    "Thanks for reaching out. I'll make sure Alex sees your message and gets "
    "back to you. If it's urgent, you can also reach him directly via the "
    "contact form.",
    True,  # always escalate fallback
)


class AIReply(NamedTuple):
    body: str
    should_escalate: bool


def generate_response(message_body: str, *, service_name: str = "") -> AIReply:
    """
    Rule-based first response to a player message.

    Returns (body, should_escalate). When should_escalate is True the thread
    status is set to ESCALATED and Alex gets a notification.

    Replace this function body with a real LLM call. The interface is stable:
    - Input:  raw message text + optional service name for context
    - Output: AIReply(body, should_escalate)
    """
    text = (message_body + " " + service_name).lower()
    for keywords, response, escalate in _RULES:
        if any(kw in text for kw in keywords):
            logger.debug("AI matched keywords %s", keywords)
            return AIReply(body=response, should_escalate=escalate)
    body, escalate = _FALLBACK
    logger.debug("AI using fallback response")
    return AIReply(body=body, should_escalate=escalate)
