"""The release claim (specs/utils/director_operating_model.md, "The release
claim"; the reference logic is wire/tests/core/validate_release_claim.py).

Five outcomes: claim, resume (same session or the same person's older
session), ask_join (held by someone who wrote within 30 minutes),
ask_takeover (held by someone silent for longer). Only claim and resume may
dispatch.
"""

from __future__ import annotations

from datetime import datetime

STALL_MINUTES = 30
TIME_FORMAT = "%Y-%m-%d %H:%M"


def minutes_since(last_write: str | None, now: str) -> float:
    if not last_write:
        return float("inf")
    try:
        return (datetime.strptime(now, TIME_FORMAT) - datetime.strptime(str(last_write), TIME_FORMAT)).total_seconds() / 60
    except ValueError:
        return float("inf")


def resolve_claim(status: dict, this_user: str, this_session: str, now: str) -> dict:
    agents = status.get("agents") or {}
    claim = agents.get("coordinator_session")
    if not claim:
        return {"outcome": "claim", "dispatch_allowed": True, "held_by": None, "age_minutes": None}
    holder = claim.get("user")
    age = minutes_since(claim.get("last_write"), now)
    if holder == this_user:
        return {"outcome": "resume", "dispatch_allowed": True, "held_by": holder,
                "rewrite_session_id": claim.get("session_id") != this_session,
                "age_minutes": None if age == float("inf") else int(age)}
    if age <= STALL_MINUTES:
        return {"outcome": "ask_join", "dispatch_allowed": False, "held_by": holder, "age_minutes": int(age)}
    return {"outcome": "ask_takeover", "dispatch_allowed": False, "held_by": holder,
            "age_minutes": None if age == float("inf") else int(age)}


def claim_block(user: str, session_id: str, branch: str, now: str, claimed_at: str | None = None) -> dict:
    return {"user": user, "session_id": session_id, "branch": branch,
            "claimed_at": claimed_at or now, "last_write": now}
