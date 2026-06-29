"""Onboarding tour: a one-time auto-start for new accounts.

Whether the tour auto-starts is decided server-side (per user, in the store) so
it fires once for a fresh login and never nags again — even across devices or
after a cache clear. theme.tour_tag() reads the flag; this endpoint records that
the tour has been seen (called when it auto-starts, and when it ends).
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from . import store

router = APIRouter()


@router.post("/api/tour/seen")
async def mark_seen() -> JSONResponse:
    store.save("tour", {"seen": True})
    return JSONResponse({"ok": True})
