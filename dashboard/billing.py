"""Billing (Stripe) — the subscription pipeline, wired early and free-by-default.

The whole sign-up + pay flow is in place so it can be exercised end-to-end
*before* anyone is ever charged. Two modes:

  - DEMO (no NEO_STRIPE_SECRET_KEY / PRICE_ID): "Join" instantly marks you active
    in the store. Zero setup — test the UI + status pipeline right now.
  - REAL (keys set): genuine Stripe Checkout. Use TEST keys + a $0 price while
    prototyping (see docs/BILLING.md). The webhook is the source of truth.

Status is stored per-instance for now (a single record). Generalize to per-user
once real accounts land (NEO-77).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from . import auth, store, theme

router = APIRouter()

SECRET_KEY = os.environ.get("NEO_STRIPE_SECRET_KEY")
PRICE_ID = os.environ.get("NEO_STRIPE_PRICE_ID")
WEBHOOK_SECRET = os.environ.get("NEO_STRIPE_WEBHOOK_SECRET")
BASE_URL = (os.environ.get("NEO_APP_URL") or "http://127.0.0.1:8000").rstrip("/")
PLAN_NAME = os.environ.get("NEO_PLAN_NAME", "Founding Beta")
PLAN_PRICE = os.environ.get("NEO_PLAN_PRICE", "$0 / month")
# Where a lapsed user goes to resubscribe. Set NEO_PAYMENT_LINK to your live
# Stripe Payment Link; falls back to the in-app Stripe Checkout page.
RESUBSCRIBE_URL = os.environ.get("NEO_PAYMENT_LINK", "")

# No real keys -> simulate the pipeline so it's testable with zero setup.
DEMO = not (SECRET_KEY and PRICE_ID)


# Subscription status is keyed per user (by login email), with a "_local"
# fallback when auth is off. One record per user under the "billing" store key.
_BLANK = {"status": "inactive", "email": None, "customer_id": None, "updated_at": None}


def _all() -> dict:
    return store.load("billing", {})


def _key(request: Request) -> str:
    return auth.current_user(request) or "_local"


def _status(request: Request) -> dict:
    return _all().get(_key(request), dict(_BLANK))


def _set(key: str, status: str, **extra) -> dict:
    data = _all()
    rec = data.get(key, dict(_BLANK))
    rec["status"] = status
    rec.update(extra)
    rec["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data[key] = rec
    store.save("billing", data)
    return rec


def is_subscribed(request: Request) -> bool:
    """For feature-gating later — true if THIS user has an active subscription."""
    return _status(request).get("status") == "active"


def _send_welcome_email(to_email: str, password: str) -> None:
    # Resend's HTTPS API — Render's free tier blocks outbound SMTP ports.
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        print(f"[billing] RESEND_API_KEY not set — credentials: {to_email} / {password}")
        return
    from_email = os.environ.get("NEO_EMAIL_FROM", "onboarding@resend.dev")
    app_url = BASE_URL
    landing = os.environ.get("NEO_LANDING_URL", "https://youraria.co")
    body = f"""Hi,

Welcome to Neo. Your private personal OS is ready.

Login here: {app_url}/login
Email:      {to_email}
Password:   {password}

Your 14-day free trial has started. You won't be charged until
day 15. Cancel anytime -- your data is always exportable.

With care,
Mariah
Co-Founder & CTO, Aria
{landing}
"""
    try:
        import resend
        resend.api_key = api_key
        resend.Emails.send({
            "from": f"Mariah at Aria <{from_email}>",
            "to": [to_email],
            "subject": "Your Neo is ready ✦",
            "text": body,
        })
        print(f"[billing] welcome email sent to {to_email}")
    except Exception as e:
        print(f"[billing] email failed: {e} — credentials: {to_email} / {password}")


# ── API ───────────────────────────────────────────────────────────────────────
@router.get("/api/billing/status")
async def billing_status(request: Request) -> JSONResponse:
    d = _status(request)
    return JSONResponse({"status": d["status"], "demo": DEMO, "plan": PLAN_NAME,
                         "price": PLAN_PRICE, "email": d.get("email"),
                         "user": auth.current_user(request)})


@router.post("/api/billing/checkout")
async def checkout(request: Request) -> JSONResponse:
    if DEMO:
        # No Stripe account needed — jump straight to the success page.
        return JSONResponse({"ok": True, "demo": True, "url": "/billing/success?demo=1"})
    key = _key(request)
    try:
        import stripe
        stripe.api_key = SECRET_KEY
        kwargs = dict(
            mode="subscription",
            line_items=[{"price": PRICE_ID, "quantity": 1}],
            success_url=f"{BASE_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{BASE_URL}/billing/cancel",
            allow_promotion_codes=True,
            client_reference_id=key,  # ties the Stripe session back to this user
            subscription_data={"trial_period_days": 14},
        )
        if "@" in key:
            kwargs["customer_email"] = key
        session = stripe.checkout.Session.create(**kwargs)
        return JSONResponse({"ok": True, "demo": False, "url": session.url})
    except Exception as e:
        print(f"[billing] checkout failed: {e}")
        return JSONResponse({"ok": False, "message": "Couldn't start checkout."}, status_code=502)


@router.post("/api/billing/reset")
async def reset(request: Request) -> JSONResponse:
    """Testing helper — clear THIS user's subscription so it can be re-run."""
    _set(_key(request), "inactive", email=None, customer_id=None)
    return JSONResponse({"ok": True})


@router.post("/api/billing/webhook")
async def webhook(request: Request) -> JSONResponse:
    """Stripe's source of truth for subscription state. Exempt from auth so
    Stripe can reach it (see auth.EXEMPT)."""
    if DEMO:
        return JSONResponse({"ok": True, "demo": True})
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        import stripe
        if WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig, WEBHOOK_SECRET)
        else:  # no signing secret configured — parse without verifying (dev only)
            event = json.loads(payload)
    except Exception as e:
        _ws = WEBHOOK_SECRET or ""
        print(f"[billing] webhook verify failed: {e} | secret_len={len(_ws)} "
              f"secret_tail=...{_ws[-4:]} payload_len={len(payload)} sig_present={bool(sig)}")
        return JSONResponse({"ok": False}, status_code=400)
    # construct_event() returns a StripeObject (no .get()); re-parse the raw
    # payload as a plain dict so .get() works. Safe for both branches above.
    parsed = json.loads(payload)
    etype = parsed["type"]
    obj = parsed["data"]["object"]
    if etype == "checkout.session.completed":
        import secrets
        # Lowercase to match auth.register()'s normalization, so the billing key
        # lines up with the login email (else a paid user reads as unsubscribed).
        email = ((obj.get("customer_details") or {}).get("email") or "").strip().lower() or None
        key = obj.get("client_reference_id") or email or "_local"
        _set(key, "active", customer_id=obj.get("customer"), email=email)

        # Create the Neo account and email credentials to the buyer.
        if email:
            password = secrets.token_urlsafe(12)
            ok, result = auth.register(email, password)
            if ok:
                _send_welcome_email(email, password)
            # If already registered, that's fine — skip (their account exists).
    elif etype in ("customer.subscription.created", "customer.subscription.updated",
                   "customer.subscription.deleted"):
        # Map the Stripe customer back to whichever user we stored it against, then
        # mirror Stripe's subscription status. Only `active`/`trialing` keep access;
        # `past_due`, `unpaid`, `canceled`, etc. (and any deletion) lock the account.
        cust = obj.get("customer")
        key = next((k for k, v in _all().items() if v.get("customer_id") == cust), None)
        if key:
            sub_status = obj.get("status")  # Stripe's subscription status
            access = (etype != "customer.subscription.deleted"
                      and sub_status in ("active", "trialing"))
            _set(key, "active" if access else "canceled")
    return JSONResponse({"ok": True})


# ── Pages ─────────────────────────────────────────────────────────────────────
@router.get("/billing", response_class=HTMLResponse)
async def billing_page() -> HTMLResponse:
    return HTMLResponse(theme.page("Plan", _BODY, active=""))


@router.get("/billing/checkout", response_class=HTMLResponse)
async def checkout_page() -> HTMLResponse:
    """The gate page for a logged-in-but-unsubscribed user: one button to start
    the trial / checkout. In DEMO mode the button activates instantly."""
    return HTMLResponse(theme.page("Start your trial", _CHECKOUT_BODY, active=""))


@router.get("/billing/success", response_class=HTMLResponse)
async def success(request: Request) -> HTMLResponse:
    # The webhook is authoritative, but mark active here too so the flow is
    # testable even without webhook forwarding running locally.
    key = _key(request)
    if not DEMO and request.query_params.get("session_id"):
        try:
            import stripe
            stripe.api_key = SECRET_KEY
            s = stripe.checkout.Session.retrieve(request.query_params["session_id"])
            _set(key, "active", customer_id=s.get("customer"),
                 email=(s.get("customer_details") or {}).get("email") or (key if "@" in key else None))
        except Exception as e:
            print(f"[billing] success retrieve failed: {e}")
    else:
        _set(key, "active", email=(key if "@" in key else "demo@local"))
    return HTMLResponse(theme.page("You're in", _SUCCESS_BODY, active=""))


@router.get("/billing/cancel", response_class=HTMLResponse)
async def cancel() -> HTMLResponse:
    return HTMLResponse(theme.page("No worries", _CANCEL_BODY, active=""))


@router.get("/billing/locked", response_class=HTMLResponse)
async def locked(request: Request) -> HTMLResponse:
    """Shown to a logged-in user whose trial/subscription has lapsed (the gate in
    auth.py sends them here). Their data is kept — they just can't reach it until
    they resubscribe."""
    email = auth.current_user(request) or ""
    if RESUBSCRIBE_URL:
        sep = "&" if "?" in RESUBSCRIBE_URL else "?"
        resub = RESUBSCRIBE_URL + (f"{sep}prefilled_email={quote(email)}" if email else "")
    else:
        resub = "/billing/checkout"
    body = _LOCKED_BODY.replace("__RESUB__", resub).replace("__EMAIL__", email)
    return HTMLResponse(theme.page("Welcome back", body, active=""))


_BODY = r"""
<style>
  .bill { max-width: 520px; margin: 10px auto; }
  .bill h1 { font-size: 38px; } .bill h1 b { color: var(--gold); font-weight: 400; }
  .bill .sub { color: var(--muted); font-size: 13px; margin: 6px 0 22px; line-height: 1.6; }
  .plan { background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 26px; }
  .plan .name { font-size: 13px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--gold); }
  .plan .price { font-family: var(--font-head); font-size: 44px; margin: 8px 0 4px; }
  .plan ul { list-style: none; margin: 16px 0; padding: 0; }
  .plan li { font-size: 13.5px; color: var(--text); padding: 6px 0; border-bottom: 1px solid var(--line-soft); }
  .plan li::before { content: "\2713  "; color: var(--gold); font-weight: 700; }
  .status { font-size: 13px; margin: 14px 0; padding: 10px 12px; border-radius: 10px; background: var(--gold-soft); border: 1px solid var(--gold-line); color: var(--text); }
  .status.inactive { background: var(--field); border-color: var(--line); color: var(--muted); }
  .demo-tag { display: inline-block; font-size: 10.5px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); border: 1px solid var(--line); border-radius: 20px; padding: 2px 10px; margin-left: 8px; }
  .bill .btn { width: 100%; padding: 13px; margin-top: 6px; }
  .reset { background: none; border: none; color: var(--muted); font-size: 12px; cursor: pointer; margin-top: 14px; text-decoration: underline; }
</style>
<main class="bill">
  <h1>Your <b>Plan</b></h1>
  <p class="sub">We're in beta, so this is free. This screen exists so the whole sign-up + billing pipeline is wired and tested before anyone is ever charged.</p>
  <div class="plan">
    <div class="name"><span id="plan-name">Founding Beta</span><span class="demo-tag" id="demo-tag" style="display:none">test pipeline</span></div>
    <div class="price" id="plan-price">$0 / month</div>
    <ul>
      <li>Everything in the app</li>
      <li>Your data stays yours</li>
      <li>Cancel anytime</li>
    </ul>
    <div class="status" id="status">Checking…</div>
    <button class="btn btn-gold" id="subscribe">Join the beta — free</button>
    <button class="reset" id="reset">Reset (testing)</button>
  </div>
</main>
<script>
const $ = (s) => document.querySelector(s);
async function load() {
  try {
    const d = await (await fetch('/api/billing/status')).json();
    $('#plan-name').textContent = d.plan || 'Plan';
    $('#plan-price').textContent = d.price || '$0 / month';
    $('#demo-tag').style.display = d.demo ? 'inline-block' : 'none';
    const st = $('#status'), active = d.status === 'active';
    st.textContent = active ? ("✓ You're active" + (d.email ? (" (" + d.email + ")") : "")) : "Not subscribed yet";
    st.classList.toggle('inactive', !active);
    $('#subscribe').style.display = active ? 'none' : 'block';
  } catch (_) {}
}
$('#subscribe').addEventListener('click', async () => {
  const out = await (await fetch('/api/billing/checkout', { method: 'POST' })).json();
  if (out.url) { location.href = out.url; } else { alert(out.message || 'Could not start checkout'); }
});
$('#reset').addEventListener('click', async () => { await fetch('/api/billing/reset', { method: 'POST' }); load(); });
load();
</script>
"""

_CHECKOUT_BODY = r"""
<style>
  .co { max-width: 460px; margin: 40px auto; text-align: center; }
  .co h1 { font-size: 34px; } .co h1 b { color: var(--gold); font-weight: 400; }
  .co .sub { color: var(--muted); font-size: 13.5px; margin: 10px 0 24px; line-height: 1.6; }
  .co .plan { background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 26px; }
  .co .name { font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--gold); }
  .co .price { font-family: var(--font-head); font-size: 40px; margin: 6px 0 2px; }
  .co .trial { font-size: 12.5px; color: var(--muted); margin-bottom: 18px; }
  .co .btn { width: 100%; padding: 13px; }
  .co .fine { font-size: 11.5px; color: var(--muted); margin-top: 14px; }
</style>
<main class="co">
  <h1>One step <b>left</b></h1>
  <p class="sub">Start your 14-day free trial. You won't be charged today, and you can cancel anytime.</p>
  <div class="plan">
    <div class="name" id="plan-name">Neo</div>
    <div class="price" id="plan-price">$9.99 / month</div>
    <div class="trial">14 days free, then your plan</div>
    <button class="btn btn-gold" id="start">Start free trial</button>
    <div class="fine">Cancel anytime · Your data is exportable · Private by default</div>
  </div>
</main>
<script>
const $ = (s) => document.querySelector(s);
(async () => {
  try {
    const d = await (await fetch('/api/billing/status')).json();
    if (d.status === 'active') { location.href = '/'; return; }
    $('#plan-name').textContent = d.plan || 'Neo';
    if (d.price) $('#plan-price').textContent = d.price;
  } catch (_) {}
})();
$('#start').addEventListener('click', async () => {
  $('#start').disabled = true;
  try {
    const out = await (await fetch('/api/billing/checkout', { method: 'POST' })).json();
    if (out.url) { location.href = out.url; }
    else { alert(out.message || 'Could not start checkout'); $('#start').disabled = false; }
  } catch (_) { alert('Network error — try again'); $('#start').disabled = false; }
});
</script>
"""

_SUCCESS_BODY = r"""
<main style="max-width:520px;margin:48px auto;text-align:center;">
  <h1 style="font-size:42px;">You're <b style="color:var(--gold);font-weight:400;">in</b> 🎉</h1>
  <p style="color:var(--muted);font-size:14px;margin:14px 0 26px;line-height:1.6;">
    Welcome to Neo. Your account's all set — taking you to your dashboard…</p>
  <a class="btn btn-gold" href="/">Go now</a>
</main>
<script>setTimeout(function(){ location.href = "/"; }, 3000);</script>
"""

_CANCEL_BODY = r"""
<main style="max-width:520px;margin:48px auto;text-align:center;">
  <h1 style="font-size:42px;">No <b style="color:var(--gold);font-weight:400;">worries</b></h1>
  <p style="color:var(--muted);font-size:14px;margin:14px 0 26px;line-height:1.6;">
    Checkout was cancelled — nothing happened. You can join anytime.</p>
  <a class="btn btn-gold" href="/billing">Back to plan</a>
</main>
"""

_LOCKED_BODY = r"""
<main style="max-width:520px;margin:48px auto;text-align:center;">
  <h1 style="font-size:40px;">Welcome <b style="color:var(--gold);font-weight:400;">back</b></h1>
  <p style="color:var(--muted);font-size:14px;margin:14px 0 8px;line-height:1.6;">
    Your trial has ended, so your dashboard is paused. Your data is safe and
    waiting — resubscribe to pick up right where you left off.</p>
  <p style="color:var(--muted);font-size:12.5px;margin:0 0 26px;">__EMAIL__</p>
  <a class="btn btn-gold" href="__RESUB__" style="display:inline-block;padding:13px 28px;">Resubscribe to Neo</a>
  <div style="margin-top:22px;">
    <button id="out" style="background:none;border:none;color:var(--muted);font-size:12.5px;cursor:pointer;text-decoration:underline;">Sign out</button>
  </div>
</main>
<script>
document.getElementById('out').addEventListener('click', async () => {
  try { await fetch('/api/logout', { method: 'POST' }); } catch (_) {}
  location.href = '/login';
});
</script>
"""
