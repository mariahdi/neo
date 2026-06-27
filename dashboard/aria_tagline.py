"""Adaptive tagline (NEO-81) — "What's your ARIA today?"

The brand's "infinitely re-definable" promise, made live: the A.R.I.A. acronym
re-expands instead of being fixed. The four letters stay constant; the meaning
flexes by day, instance, and user.

  - A curated bank rotates a different expansion each day.
  - Anyone can submit their own four words (A / R / I / A) as their personal
    tagline — and it goes into a PENDING queue.
  - The owner personally approves every public expansion (nothing bad ever
    stands for ARIA). Approved ones join the rotating bank and can be voted on.
  - Everything exports to CSV (for the word-cloud chart).

Stores: "aria_personal" {user: [4 words]} and "aria_bank" {approved, pending}.
"""
from __future__ import annotations

import re
from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel

from . import auth, profile, registry, store, theme

router = APIRouter()

# The fixed official anchor — always a valid ARIA, cited when someone asks "what
# does it stand for." Everything else flexes.
ANCHOR = ["Advancing", "Real-world", "Intelligence", "Autonomy"]

# Curated starter bank (each word begins A, R, I, A).
STARTERS = [
    ["Always", "Ready", "Infinitely", "Adaptable"],
    ["Add", "Rest", "Ignore", "Admin"],
    ["Aspire", "Reach", "Inspire", "Achieve"],
    ["Adorable", "Reliable", "Intuitive", "Ally"],
    ["Always", "Rising", "Inspiring", "Action"],
    ["Actually", "Remembers", "Important", "Appointments"],
    ["Always", "Reassuring", "Infinitely", "Adaptable"],
    ["Ambitious", "Reliable", "Iconic", "Assistant"],
    ["Awake", "Rested", "Inspired", "Aligned"],
    ["Anything's", "Reachable", "Infinitely", "Achievable"],
    ["Adventure", "Requires", "Intentional", "Action"],
    ["Aim", "Refine", "Iterate", "Achieve"],
]


def _starters() -> list:
    """Per-instance bank if the profile sets one (e.g. Nessa's calming set), else default."""
    return profile.ACTIVE.get("aria_bank") or STARTERS


def _personal() -> dict:
    return store.load("aria_personal", {})


def _bank() -> dict:
    b = store.load("aria_bank", {"approved": [], "pending": []})
    b.setdefault("approved", [])
    b.setdefault("pending", [])
    return b


def _key(request: Request) -> str:
    return auth.current_user(request) or "_local"


def _clean(words) -> list[str] | None:
    """Validate a submission: exactly four words beginning A, R, I, A."""
    if not isinstance(words, list) or len(words) != 4:
        return None
    words = [str(w).strip() for w in words]
    if not all(words):
        return None
    for w, letter in zip(words, "ARIA"):
        if w[:1].upper() != letter:
            return None
    return words


def _phrase(words) -> str:
    return " ".join(words)


def _slug(words) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _phrase(words).lower()).strip("-")


def _all_phrases_lower(bank) -> set[str]:
    return {_phrase(w).lower() for w in _starters()} \
        | {_phrase(e["words"]).lower() for e in bank["approved"]} \
        | {_phrase(e["words"]).lower() for e in bank["pending"]}


# ── API ───────────────────────────────────────────────────────────────────────
@router.get("/api/aria/today")
async def today(request: Request) -> JSONResponse:
    mine = _personal().get(_key(request))
    if mine:
        return JSONResponse({"words": mine, "phrase": _phrase(mine), "source": "you",
                             "anchor": _phrase(ANCHOR)})
    pool = _starters() + [e["words"] for e in _bank()["approved"]]
    words = pool[date.today().toordinal() % len(pool)]
    return JSONResponse({"words": words, "phrase": _phrase(words), "source": "daily",
                         "anchor": _phrase(ANCHOR)})


class WordsIn(BaseModel):
    words: list = []


@router.post("/api/aria/mine")
async def set_mine(request: Request, body: WordsIn) -> JSONResponse:
    words = _clean(body.words)
    if not words:
        return JSONResponse({"ok": False, "message": "Give four words starting with A, R, I, A."},
                            status_code=400)
    personal = _personal()
    personal[_key(request)] = words
    store.save("aria_personal", personal)
    # Queue for public approval (unless it already exists somewhere).
    bank = _bank()
    if _phrase(words).lower() not in _all_phrases_lower(bank):
        bank["pending"].append({"id": _slug(words), "words": words, "by": _key(request)})
        store.save("aria_bank", bank)
    return JSONResponse({"ok": True, "phrase": _phrase(words)})


@router.get("/api/aria/bank")
async def bank() -> JSONResponse:
    b = _bank()
    return JSONResponse({"starters": [{"words": w} for w in _starters()], "approved": b["approved"]})


class IdIn(BaseModel):
    id: str = ""


@router.post("/api/aria/vote")
async def vote(body: IdIn) -> JSONResponse:
    b = _bank()
    for e in b["approved"]:
        if e.get("id") == body.id:
            e["votes"] = e.get("votes", 0) + 1
    store.save("aria_bank", b)
    return JSONResponse({"ok": True})


# ── Owner-only moderation ──────────────────────────────────────────────────────
@router.get("/api/aria/pending")
async def pending() -> JSONResponse:
    if not registry.is_owner():
        return JSONResponse({"error": "owner only"}, status_code=403)
    return JSONResponse(_bank()["pending"])


@router.post("/api/aria/approve")
async def approve(body: IdIn) -> JSONResponse:
    if not registry.is_owner():
        return JSONResponse({"error": "owner only"}, status_code=403)
    b = _bank()
    item = next((x for x in b["pending"] if x["id"] == body.id), None)
    if item:
        b["pending"] = [x for x in b["pending"] if x["id"] != body.id]
        item.setdefault("votes", 0)
        b["approved"].append(item)
        store.save("aria_bank", b)
    return JSONResponse({"ok": True})


@router.post("/api/aria/reject")
async def reject(body: IdIn) -> JSONResponse:
    if not registry.is_owner():
        return JSONResponse({"error": "owner only"}, status_code=403)
    b = _bank()
    b["pending"] = [x for x in b["pending"] if x["id"] != body.id]
    store.save("aria_bank", b)
    return JSONResponse({"ok": True})


@router.get("/api/aria/export.csv")
async def export_csv() -> Response:
    if not registry.is_owner():
        return Response("owner only", status_code=403)
    b = _bank()
    rows = [("A", "R", "I", "A", "phrase", "by", "status", "votes")]
    for e in b["approved"]:
        rows.append((*e["words"], _phrase(e["words"]), e.get("by", ""), "approved", e.get("votes", 0)))
    for e in b["pending"]:
        rows.append((*e["words"], _phrase(e["words"]), e.get("by", ""), "pending", 0))
    csv = "\n".join(",".join('"' + str(c).replace('"', '""') + '"' for c in r) for r in rows)
    return Response(csv, media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="aria-expansions.csv"'})


# ── Page ──────────────────────────────────────────────────────────────────────
@router.get("/aria", response_class=HTMLResponse)
async def aria_page() -> HTMLResponse:
    owner = "1" if registry.is_owner() else ""
    return HTMLResponse(theme.page("ARIA", _BODY.replace("<!--OWNER-->", owner), active=""))


_BODY = r"""
<style>
  .aw { max-width: 640px; margin: 10px auto; }
  .aw h1 { font-size: 34px; } .aw h1 b { color: var(--gold); font-weight: 400; }
  .aw .sub { color: var(--muted); font-size: 13px; margin: 6px 0 22px; line-height: 1.6; }
  .today { background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 26px; text-align: center; margin-bottom: 18px; }
  .today .mark { font-family: var(--font-head); font-size: 30px; letter-spacing: 0.16em; }
  .today .mark b { color: var(--gold); }
  .today .exp { font-size: 19px; margin-top: 10px; line-height: 1.5; }
  .today .exp b { color: var(--gold); }
  .today .src { font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); margin-top: 10px; }
  .card { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 14px; padding: 20px; margin-bottom: 16px; }
  .card h2 { font-size: 17px; margin-bottom: 4px; } .card p { font-size: 12.5px; color: var(--muted); margin-bottom: 14px; }
  .words { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
  .words .wl { font-size: 11px; color: var(--gold); font-weight: 700; text-align: center; margin-bottom: 3px; }
  .msg { display:none; margin-top:12px; font-size:13px; padding:9px 12px; border-radius:9px; background:var(--gold-soft); border:1px solid var(--gold-line); color:var(--text); }
  .msg.show { display:block; }
  .cloud { display: flex; flex-wrap: wrap; gap: 10px 16px; align-items: baseline; }
  .cloud span { cursor: pointer; color: var(--text); }
  .cloud span:hover { color: var(--gold); }
  .pend { display:flex; align-items:center; justify-content:space-between; gap:10px; padding:9px 0; border-bottom:1px solid var(--line-soft); font-size:13.5px; }
  .pend .acts { display:flex; gap:6px; }
  .anchor { font-size: 12px; color: var(--muted); text-align:center; margin-top: 6px; }
  .anchor b { color: var(--gold); }
</style>
<main class="aw">
  <h1>What's your <b>ARIA</b> today?</h1>
  <p class="sub">ARIA is infinitely re-definable — the four letters stay, the meaning flexes. Here's today's; make your own below.</p>

  <div class="today">
    <div class="mark">ARI<b>A</b></div>
    <div class="exp" id="today-exp">…</div>
    <div class="src" id="today-src"></div>
  </div>
  <div class="anchor">Officially: <span id="anchor"></span></div>

  <div class="card" style="margin-top:18px;">
    <h2>Make it yours</h2>
    <p>Four words — beginning <b>A</b>, <b>R</b>, <b>I</b>, <b>A</b>. It becomes your tagline, and (once approved) joins the bank for everyone.</p>
    <div class="words">
      <div><div class="wl">A</div><input id="w0" type="text" placeholder="Always"></div>
      <div><div class="wl">R</div><input id="w1" type="text" placeholder="Ready"></div>
      <div><div class="wl">I</div><input id="w2" type="text" placeholder="Infinitely"></div>
      <div><div class="wl">A</div><input id="w3" type="text" placeholder="Adaptable"></div>
    </div>
    <div style="margin-top:14px;"><button class="btn btn-gold" id="save-mine">Make it mine</button></div>
    <div class="msg" id="mine-msg"></div>
  </div>

  <div class="card">
    <h2>The bank</h2>
    <p>Approved expansions — tap to vote. Bigger = more loved.</p>
    <div class="cloud" id="cloud"></div>
  </div>

  <div class="card" id="owner-card" style="display:none;">
    <h2>Pending approval <span style="font-size:12px;color:var(--muted);">(owner)</span></h2>
    <p>Nothing stands for ARIA until you approve it. <a href="/api/aria/export.csv">Download CSV ↓</a></p>
    <div id="pending"></div>
  </div>
</main>
<script>
const $ = (s) => document.querySelector(s);
const IS_OWNER = "<!--OWNER-->" === "1";
const html4 = (words) => words.map(w => "<b>"+w[0]+"</b>"+w.slice(1)).join(" ");

async function loadToday() {
  const d = await (await fetch("/api/aria/today")).json();
  $("#today-exp").innerHTML = html4(d.words);
  $("#today-src").textContent = d.source === "you" ? "your tagline" : "today's pick";
  $("#anchor").innerHTML = html4(d.anchor.split(" "));
}
async function loadBank() {
  const b = await (await fetch("/api/aria/bank")).json();
  const items = (b.approved || []).slice().sort((a,c)=>(c.votes||0)-(a.votes||0));
  $("#cloud").innerHTML = items.length ? items.map(e => {
    const size = 13 + Math.min(14, (e.votes||0)*2);
    return `<span data-id="${e.id}" style="font-size:${size}px">${html4(e.words)} <small style="color:var(--muted)">(${e.votes||0})</small></span>`;
  }).join("") : '<span style="color:var(--muted);cursor:default">No approved expansions yet — be the first below.</span>';
  $("#cloud").querySelectorAll("[data-id]").forEach(s => s.addEventListener("click", async () => {
    await fetch("/api/aria/vote", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({id:s.dataset.id})});
    loadBank();
  }));
}
async function loadPending() {
  if (!IS_OWNER) return;
  $("#owner-card").style.display = "block";
  const list = await (await fetch("/api/aria/pending")).json();
  const wrap = $("#pending");
  wrap.innerHTML = (list && list.length) ? list.map(e => `
    <div class="pend"><span>${html4(e.words)} <small style="color:var(--muted)">— ${e.by||""}</small></span>
      <span class="acts"><button class="btn btn-sm" data-ap="${e.id}">Approve</button><button class="btn btn-sm" data-rj="${e.id}">Reject</button></span></div>`).join("")
    : '<div style="color:var(--muted);font-size:13px;">Nothing pending.</div>';
  wrap.querySelectorAll("[data-ap]").forEach(b => b.addEventListener("click", () => act("approve", b.dataset.ap)));
  wrap.querySelectorAll("[data-rj]").forEach(b => b.addEventListener("click", () => act("reject", b.dataset.rj)));
}
async function act(kind, id) {
  await fetch("/api/aria/"+kind, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({id})});
  loadPending(); loadBank();
}
$("#save-mine").addEventListener("click", async () => {
  const words = [0,1,2,3].map(i => $("#w"+i).value.trim());
  const out = await (await fetch("/api/aria/mine", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({words})})).json();
  const m = $("#mine-msg"); m.classList.add("show");
  m.innerHTML = out.ok ? ("✓ Saved — that's your ARIA now. Sent for approval to join the bank.") : (out.message || "Couldn't save that.");
  if (out.ok) { loadToday(); }
});
loadToday(); loadBank(); loadPending();
</script>
"""
