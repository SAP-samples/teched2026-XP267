"""Per-request user-token context for the Order Fulfillment Advisor agent.

The A2A server receives the end user's bearer token on each request.
`JWTContextMiddleware` (in `main.py`) stores it here in a context variable so the
agent can read it later — without the token the agent cannot key a per-user
conversation thread.

`get_user_sub()` returns the token's `sub` claim, which `agent.py` uses as the
checkpointer `thread_id` so each user gets their own conversation memory.
"""

import base64
import json
from contextvars import ContextVar, Token

# Per-request user token, set by JWTContextMiddleware via set_user_token().
_user_token_context: ContextVar[str | None] = ContextVar("user_token", default=None)


def set_user_token(token: str | None) -> Token:
    """Store the user token for the current async context; returns a reset handle."""
    return _user_token_context.set(token)


def reset_user_token(token: Token) -> None:
    """Restore the user-token context to its value before the matching set_user_token()."""
    _user_token_context.reset(token)


def get_user_sub() -> str:
    """Return the `sub` claim from the current request's JWT, or a fallback.

    Decodes the JWT payload (middle segment) without verifying the signature —
    the platform has already verified it before the request reaches this code.
    Used only to key per-user conversation memory, so if no token is present or
    it cannot be decoded we fall back to a stable default rather than failing the
    request.
    """
    token = _user_token_context.get()
    if not token:
        return "anonymous"

    try:
        payload_segment = token.split(".")[1]
        padding = 4 - len(payload_segment) % 4
        if padding != 4:
            payload_segment += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_segment))
        return payload.get("sub") or "anonymous"
    except Exception:
        return "anonymous"
