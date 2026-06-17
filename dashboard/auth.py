"""Session login (NEO-33) — mock auth with the plumbing for a real backend.

Replaces the browser's Basic-Auth popup with a proper /login screen and a
persistent session, so you don't re-authenticate every load:

  - On login we issue an HMAC-signed session token. It's set as a cookie (so
    page navigations and same-origin fetches are authorized server-side) and
    also handed back in the response for the client to keep in localStorage.
  - A returning visitor skips the login screen: the cookie keeps them signed
    in, and /login bounces them straight to the dashboard.
  - Logout clears both the cookie and localStorage.

Enforcement stays server-side (the cookie), so the public deployment is still
protected — only on when DASHBOARD_USER/DASHBOARD_PASS are set, same as before;
local/demo runs are open.

Dropping in REAL auth = replace `_check_credentials()` (swap the single env
user for a real user store) and, if you like, the token issue/verify (e.g.
JWTs). The middleware, routes, cookie, and client flow stay exactly the same —
the frontend already keeps the token in localStorage for a bearer-style API.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from . import theme

USER = os.environ.get("DASHBOARD_USER")
PASS = os.environ.get("DASHBOARD_PASS")
AUTH_ON = bool(USER and PASS)

COOKIE = "neo_session"
TTL = 60 * 60 * 24 * 30  # 30 days
# Signing key: explicit SESSION_SECRET, else derived from the password so it's
# stable across restarts without extra config. Rotating either logs everyone out.
_SECRET = (os.environ.get("SESSION_SECRET") or PASS or "neo-dev-secret").encode()

# Reachable without a session (the login screen and its API).
EXEMPT = {"/login", "/api/login", "/api/logout"}


# ── Tokens (mock; swap for JWTs in a real backend) ────────────────────────────
def _sign(payload: str) -> str:
    return hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()


def make_token(user: str) -> str:
    payload = f"{user}|{int(time.time()) + TTL}"
    raw = f"{payload}|{_sign(payload)}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def valid_token(token: str) -> bool:
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        user, exp, sig = raw.rsplit("|", 2)
        if not hmac.compare_digest(sig, _sign(f"{user}|{exp}")):
            return False
        return int(exp) > time.time()
    except Exception:
        return False


def _check_credentials(username: str, password: str) -> bool:
    """MOCK: one shared user from the environment. Replace with a real user
    store (DB lookup + password hash) and the rest of the flow is unchanged."""
    if not AUTH_ON:
        return True  # local/demo — no credentials configured
    return (hmac.compare_digest(username or "", USER or "")
            and hmac.compare_digest(password or "", PASS or ""))


def _token_from(request: Request) -> str | None:
    tok = request.cookies.get(COOKIE)
    if tok:
        return tok
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:]
    return request.headers.get("X-Session-Token")


# ── Middleware ────────────────────────────────────────────────────────────────
class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not AUTH_ON:
            return await call_next(request)
        path = request.url.path
        if path in EXEMPT:
            return await call_next(request)
        token = _token_from(request)
        if token and valid_token(token):
            return await call_next(request)
        if path.startswith("/api/"):
            return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
        return RedirectResponse(url="/login", status_code=302)


# ── Routes ────────────────────────────────────────────────────────────────────
router = APIRouter()


class LoginIn(BaseModel):
    username: str = ""
    password: str = ""


@router.post("/api/login")
async def login(body: LoginIn) -> JSONResponse:
    if _check_credentials(body.username, body.password):
        token = make_token(body.username or "user")
        resp = JSONResponse({"ok": True, "token": token})
        # httponly cookie does enforcement; the body token is for localStorage.
        resp.set_cookie(COOKIE, token, max_age=TTL, httponly=True, samesite="lax", path="/")
        return resp
    return JSONResponse({"ok": False, "message": "Wrong username or password."}, status_code=401)


@router.post("/api/logout")
async def logout() -> JSONResponse:
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE, path="/")
    return resp


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # Already signed in? Skip the screen.
    token = request.cookies.get(COOKIE)
    if AUTH_ON and token and valid_token(token):
        return RedirectResponse(url="/", status_code=302)
    return HTMLResponse(_LOGIN_PAGE)


_LOGIN_PAGE = (
    """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sign in — <!--LNAME--></title>
<!--LFONTS-->
<style>"""
    + theme.BASE_CSS
    + """
  body { display: flex; align-items: center; justify-content: center; padding: 24px; }
  .login { width: 100%; max-width: 360px; }
  .login .brand { display: block; text-align: center; font-size: 52px; letter-spacing: 0.14em; margin-bottom: 4px; }
  .login .brand b { color: var(--gold); }
  .login .tag { text-align: center; font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase; color: var(--muted); margin-bottom: 26px; }
  .login .card { padding: 26px 24px; }
  .login label { display: block; font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); margin: 0 0 6px; }
  .login input { width: 100%; margin-bottom: 16px; }
  .login .btn-gold { width: 100%; padding: 12px; }
  .login .err { display: none; font-size: 12.5px; color: #f0cda0; background: rgba(217,138,58,0.12); border: 1px solid rgba(217,138,58,0.5); border-radius: 9px; padding: 9px 11px; margin-bottom: 14px; }
  .login .err.show { display: block; }
</style>
</head>
<body>
  <form class="login" id="login-form">
    <span class="brand"><!--LWORD--></span>
    <div class="tag"><!--LTAG--></div>
    <div class="card">
      <div class="err" id="err"></div>
      <label for="u">Username</label>
      <input id="u" type="text" autocomplete="username" autofocus>
      <label for="p">Password</label>
      <input id="p" type="password" autocomplete="current-password">
      <button type="submit" class="btn btn-gold">Sign in</button>
    </div>
  </form>
<script>
  const form = document.getElementById("login-form");
  const err = document.getElementById("err");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    err.classList.remove("show");
    const username = document.getElementById("u").value;
    const password = document.getElementById("p").value;
    try {
      const r = await fetch("/api/login", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ username, password }) });
      const out = await r.json();
      if (out.ok) {
        localStorage.setItem("neo_session", out.token);  // returning users skip this screen
        location.href = "/";
      } else {
        err.textContent = out.message || "Sign in failed."; err.classList.add("show");
      }
    } catch (_) { err.textContent = "Network error — try again."; err.classList.add("show"); }
  });
</script>
</body>
</html>"""
)

# Brand the login screen for the active profile (wordmark, name, fonts, tagline).
_LOGIN_PAGE = (
    _LOGIN_PAGE.replace("<!--LNAME-->", theme.ACTIVE["name"])
    .replace("<!--LFONTS-->", theme.FONT_LINK)
    .replace("<!--LWORD-->", theme.ACTIVE["wordmark"])
    .replace("<!--LTAG-->", theme.ACTIVE["tagline"])
)
