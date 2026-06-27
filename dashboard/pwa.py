"""PWA (NEO-88) — make Neo installable on phones/desktops.

Serves a per-instance web manifest and a small service worker so browsers offer
"Install" / "Add to Home Screen" and the app opens in its own window. Icons live
in dashboard/static/. The service worker is served from "/" so its scope covers
the whole app; it does network-first with a cache fallback (basic offline).
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

from . import profile

router = APIRouter()


@router.get("/manifest.webmanifest")
async def manifest() -> JSONResponse:
    name = profile.ACTIVE.get("name", "Neo")
    bg = profile.ACTIVE.get("tokens", {}).get("bg", "#0f1115")
    data = {
        "name": name,
        "short_name": name,
        "description": profile.ACTIVE.get("tagline", "Your personal OS"),
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": bg,
        "theme_color": bg,
        "icons": [
            {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }
    return JSONResponse(data, media_type="application/manifest+json")


_SW = """
const CACHE = 'neo-v1';
self.addEventListener('install', (e) => { self.skipWaiting(); });
self.addEventListener('activate', (e) => { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  e.respondWith(
    fetch(req).then((res) => {
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
      return res;
    }).catch(() => caches.match(req))
  );
});
"""


@router.get("/sw.js")
async def service_worker() -> Response:
    return Response(_SW, media_type="application/javascript")
