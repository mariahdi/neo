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
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from . import store, theme

USER = os.environ.get("DASHBOARD_USER")
PASS = os.environ.get("DASHBOARD_PASS")
AUTH_ON = bool(USER and PASS)

# Owner accounts are never sent through the billing gate (you shouldn't have to
# subscribe to your own app). Set NEO_OWNER_EMAILS=a@x.com,b@y.com; the legacy
# env user (if set) is always an owner.
OWNER_EMAILS = {e.strip().lower() for e in (os.environ.get("NEO_OWNER_EMAILS") or "").split(",") if e.strip()}
if USER:
    OWNER_EMAILS.add(USER.strip().lower())


def is_owner_email(email: str | None) -> bool:
    return bool(email) and email.strip().lower() in OWNER_EMAILS

COOKIE = "neo_session"
TTL = 60 * 60 * 24 * 30  # 30 days
# Signing key for session tokens. Priority:
#   1. SESSION_SECRET — explicit, strong, stable across restarts (recommended).
#   2. PASS           — legacy: derived from the env password (stable, tied to it).
#   3. a random per-process key — only when neither is set; NEVER a public
#      hardcoded default. Safe even if accounts are created at runtime; the only
#      cost is sessions resetting on restart until SESSION_SECRET is set.
_RUNTIME_SECRET = None


def _secret() -> bytes:
    explicit = os.environ.get("SESSION_SECRET")
    if explicit:
        return explicit.encode()
    if PASS:
        return PASS.encode()
    global _RUNTIME_SECRET
    if _RUNTIME_SECRET is None:
        _RUNTIME_SECRET = os.urandom(32)
    return _RUNTIME_SECRET


if not os.environ.get("SESSION_SECRET") and (PASS or os.environ.get("NEO_AUTH")):
    print("[auth] WARNING: SESSION_SECRET is not set. "
          + ("Deriving the session key from DASHBOARD_PASS (rotating the password logs everyone out). "
             if PASS else "Using a random key that resets on every restart (users get logged out). ")
          + "Set SESSION_SECRET (e.g. `openssl rand -hex 32`) for stable, secure sessions.")

# Reachable without a session: the login screen + its API, server-to-server
# account provisioning (GHL calls this after purchase), and the Stripe webhook.
EXEMPT = {"/login", "/api/login", "/api/logout", "/api/provision", "/api/billing/webhook"}

# Marketing/landing URL shown on the login screen ("Get Neo"). Point
# NEO_LANDING_URL at the GHL landing page once it's live.
LANDING_URL = os.environ.get("NEO_LANDING_URL", "#")


# ── Tokens (mock; swap for JWTs in a real backend) ────────────────────────────
def _sign(payload: str) -> str:
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()


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


# ── Real user store (NEO-77) — replaces the mock single env user ───────────────
# Users live in the key/value store under "users": {email: {salt, hash, created}}.
# Passwords are hashed with PBKDF2-HMAC-SHA256 (stdlib) — never stored in plain.
def _users() -> dict:
    return store.load("users", {})


def _hash_pw(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", (password or "").encode(), bytes.fromhex(salt), 200_000).hex()


def register(email: str, password: str) -> tuple[bool, str]:
    """Create a user. Returns (ok, normalized-email) or (False, error-message)."""
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return False, "Enter a valid email."
    if len(password or "") < 8:
        return False, "Password must be at least 8 characters."
    users = _users()
    if email in users:
        return False, "That email is already registered."
    salt = os.urandom(16).hex()
    users[email] = {"salt": salt, "hash": _hash_pw(password, salt),
                    "created": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    store.save("users", users)
    return True, email


def set_password(email: str, password: str) -> tuple[bool, str]:
    """Reset the password for an existing user. Returns (ok, normalized-email)
    or (False, error-message)."""
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return False, "Enter a valid email."
    if len(password or "") < 8:
        return False, "Password must be at least 8 characters."
    users = _users()
    if email not in users:
        return False, "No account found for that email."
    salt = os.urandom(16).hex()
    users[email]["salt"] = salt
    users[email]["hash"] = _hash_pw(password, salt)
    store.save("users", users)
    return True, email


def verify_user(email: str, password: str) -> bool:
    u = _users().get((email or "").strip().lower())
    if not u:
        return False
    return hmac.compare_digest(u.get("hash", ""), _hash_pw(password, u.get("salt", "")))


def auth_on() -> bool:
    """Gate is on if a legacy env user is set, any account exists, or NEO_AUTH is
    set. Local/demo (none of these) stays open — unchanged behavior."""
    return bool(USER and PASS) or bool(_users()) or bool(os.environ.get("NEO_AUTH"))


def _check_credentials(username: str, password: str) -> bool:
    """Verify against the real user store, with the env user as a bootstrap admin.
    The middleware / cookie / token flow is unchanged."""
    if not auth_on():
        return True  # local/demo — nothing configured
    if USER and PASS and hmac.compare_digest(username or "", USER) and hmac.compare_digest(password or "", PASS):
        return True
    return verify_user(username, password)


def _token_from(request: Request) -> str | None:
    tok = request.cookies.get(COOKIE)
    if tok:
        return tok
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:]
    return request.headers.get("X-Session-Token")


def user_from_token(token: str) -> str | None:
    """The user a valid token belongs to (None if missing/invalid/expired)."""
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        user, exp, sig = raw.rsplit("|", 2)
        if not hmac.compare_digest(sig, _sign(f"{user}|{exp}")):
            return None
        return user if int(exp) > time.time() else None
    except Exception:
        return None


def current_user(request: Request) -> str | None:
    """Who's logged in on this request (their login email), or None."""
    tok = _token_from(request)
    return user_from_token(tok) if tok else None


# ── Middleware ────────────────────────────────────────────────────────────────
class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not auth_on():
            return await call_next(request)
        path = request.url.path
        if path in EXEMPT:
            return await call_next(request)
        token = _token_from(request)
        if token and valid_token(token):
            # A valid session is all Neo checks — billing lives entirely in GHL.
            return await call_next(request)
        if path.startswith("/api/"):
            return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
        return RedirectResponse(url="/login", status_code=302)


class UserContextMiddleware:
    """Pure-ASGI middleware: resolve the session user and set it for per-user
    data scoping (NEO-93). Pure ASGI (not BaseHTTPMiddleware) and added outermost
    so the contextvar reliably propagates into the endpoint's task."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            store.set_current_user(self._user(scope))
        await self.app(scope, receive, send)

    @staticmethod
    def _user(scope):
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        tok = None
        for part in headers.get("cookie", "").split(";"):
            part = part.strip()
            if part.startswith(COOKIE + "="):
                tok = part[len(COOKIE) + 1:]
                break
        if not tok:
            ah = headers.get("authorization", "")
            tok = ah[7:] if ah.startswith("Bearer ") else headers.get("x-session-token")
        return user_from_token(tok) if tok else None


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
    return JSONResponse({"ok": False, "message": "Wrong email or password."}, status_code=401)


PROVISION_SECRET = os.environ.get("NEO_PROVISION_SECRET")


class ProvisionIn(BaseModel):
    email: str = ""
    password: str = ""
    provision_secret: str = ""
    force: bool = False   # if the account already exists, reset its password instead of failing


@router.post("/api/provision")
async def provision(body: ProvisionIn) -> JSONResponse:
    """Server-to-server account creation, called by the GHL workflow after a
    purchase. Not user-facing — guarded by a shared secret, never a session.
    With force=True, an existing account's password is reset instead of erroring."""
    if not PROVISION_SECRET or not hmac.compare_digest(body.provision_secret or "", PROVISION_SECRET):
        return JSONResponse({"ok": False, "message": "unauthorized"}, status_code=403)
    ok, result = set_password(body.email, body.password) if body.force else register(body.email, body.password)
    if not ok:
        return JSONResponse({"ok": False, "message": result}, status_code=400)
    return JSONResponse({"ok": True, "email": result}, status_code=201)


@router.post("/api/logout")
async def logout() -> JSONResponse:
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE, path="/")
    return resp


class MigrateIn(BaseModel):
    from_user: str = ""
    to_user: str = ""


@router.post("/api/admin/migrate-data")
async def migrate_data(request: Request, body: MigrateIn) -> JSONResponse:
    """Owner-only one-time data move between login identities."""
    if not is_owner_email(current_user(request)):
        return JSONResponse({"ok": False, "error": "owner only"}, status_code=403)
    moved = store.migrate_user(body.from_user.strip(), body.to_user.strip())
    return JSONResponse({"ok": True, "moved": moved, "count": len(moved)})


@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    if not is_owner_email(current_user(request)):
        return RedirectResponse(url="/", status_code=302)
    return HTMLResponse(theme.page("Admin", _ADMIN_BODY, active=""))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # Already signed in? Skip the screen.
    token = request.cookies.get(COOKIE)
    if auth_on() and token and valid_token(token):
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
  .login .switch { text-align: center; font-size: 12.5px; color: var(--muted); margin-top: 14px; }
  .login .switch a { color: var(--gold); text-decoration: none; cursor: pointer; }
</style>
</head>
<body>
  <form class="login" id="login-form">
    <span class="brand"><!--LWORD--></span>
    <div class="tag"><!--LTAG--></div>
    <div class="card">
      <div class="err" id="err"></div>
      <label for="u">Email</label>
      <input id="u" type="text" autocomplete="username" autofocus>
      <label for="p">Password</label>
      <input id="p" type="password" autocomplete="current-password">
      <button type="submit" id="submit-btn" class="btn btn-gold">Sign in</button>
      <div class="switch">Don't have an account? <a href="<!--LANDING-->">Get Neo</a></div>
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
    .replace("<!--LANDING-->", LANDING_URL)
)


_ADMIN_BODY = r"""
<main style="max-width:520px;margin:20px auto;">
  <h1 style="font-size:34px;">Admin</h1>
  <p style="color:var(--muted);font-size:13px;margin:8px 0 20px;line-height:1.6;">
    One-time data migration. Move a user's data (recipes, about, etc.) from one
    login identity to another — e.g. your old env login to your account email.
    Shared data (accounts, billing) is never touched, and it's safe to re-run.</p>
  <div class="card">
    <label style="display:block;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:0 0 5px;">From (old identity)</label>
    <input id="from" type="text" style="width:100%;margin-bottom:14px;" placeholder="your old DASHBOARD_USER value">
    <label style="display:block;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:0 0 5px;">To (new account email)</label>
    <input id="to" type="text" style="width:100%;margin-bottom:16px;" placeholder="you@email.com">
    <button class="btn btn-gold" id="go">Migrate data</button>
    <div id="res" style="margin-top:14px;font-size:13px;color:var(--gold);line-height:1.5;"></div>
  </div>
</main>
<script>
const $=(s)=>document.querySelector(s);
$("#go").addEventListener("click", async ()=>{
  $("#go").disabled=true; $("#res").textContent="Migrating…";
  try{
    const out = await (await fetch("/api/admin/migrate-data",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({from_user:$("#from").value, to_user:$("#to").value})})).json();
    $("#res").textContent = out.ok ? ("Moved "+out.count+" item(s): "+((out.moved||[]).join(", ")||"nothing new")) : ("Error: "+(out.error||"failed"));
  }catch(_){ $("#res").textContent="Network error."; }
  $("#go").disabled=false;
});
</script>
"""
