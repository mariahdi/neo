"""Wins (NEO-32) — daily accomplishment tracking with a Claude layer.

Log what went well, grouped by day and tagged work / life / health / build.
You can add wins by hand, or tell Neo about your day and a live Anthropic call
*recognizes* the accomplishments and offers them as suggestions — you confirm
each before it's saved, so nothing is logged silently and one sentence can
surface several wins. A keyword heuristic stands in when no key is set.

Persists to the JSON store (dashboard/data/wins.json).
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import date

import requests
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from . import store, theme

router = APIRouter()

ANTHROPIC_KEY = os.environ.get("NEO_ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.environ.get("NEO_ANTHROPIC_MODEL", "claude-sonnet-4-6")

CATEGORIES = ["work", "life", "health", "build"]

# A couple of sample wins so the page isn't empty on first load.
DEFAULT = {"wins": []}


def _data() -> dict:
    return store.load("wins", DEFAULT)


def _norm_cat(c: str) -> str:
    c = (c or "").strip().lower()
    return c if c in CATEGORIES else "life"


# ── Recognition layer ─────────────────────────────────────────────────────────
def _suggest_claude(text: str) -> list[dict]:
    """Live Anthropic call: pull distinct accomplishments out of free text."""
    prompt = (
        "You help someone log their daily wins. Categories: "
        f"{', '.join(CATEGORIES)}.\n"
        f'They described their day: "{text}"\n\n'
        "Extract each distinct accomplishment worth celebrating as a separate "
        "win. Reply with ONLY a JSON array, no prose:\n"
        '[{"text": "<concise win, past tense>", "category": "<one of the four>"}]\n'
        "Return [] if there are no real accomplishments."
    )
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": ANTHROPIC_MODEL, "max_tokens": 400,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=40,
    )
    resp.raise_for_status()
    raw = resp.json()["content"][0]["text"].strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        raw = raw[4:] if raw.startswith("json") else raw
    items = json.loads(raw.strip())
    return [{"text": (i.get("text") or "").strip(), "category": _norm_cat(i.get("category"))}
            for i in items if (i.get("text") or "").strip()]


_CAT_HINTS = {
    "health": ("gym", "ran", "run", "walk", "workout", "weigh", "slept", "ate", "doctor", "meditat", "yoga"),
    "build": ("shipped", "built", "coded", "deployed", "fixed", "merged", "bug", "neo", "dashboard", "feature"),
    "work": ("call", "called", "email", "meeting", "client", "sent", "finished", "report", "proposal", "presentation"),
}


def _suggest_mock(text: str) -> list[dict]:
    """Offline stand-in: split into clauses, keep accomplishment-like ones."""
    clauses = re.split(r"\s*(?:,|;|\band\b|\bthen\b|\balso\b)\s*", text, flags=re.I)
    out = []
    for c in clauses:
        c = c.strip().rstrip(".")
        if len(c) < 4:
            continue
        low = c.lower()
        cat = "life"
        for category, hints in _CAT_HINTS.items():
            if any(h in low for h in hints):
                cat = category
                break
        out.append({"text": c[0].upper() + c[1:], "category": cat})
    return out[:6]


# ── API ───────────────────────────────────────────────────────────────────────
@router.get("/api/wins")
async def get_wins() -> JSONResponse:
    return JSONResponse(_data())


class SuggestIn(BaseModel):
    text: str


@router.post("/api/wins/suggest")
async def suggest_wins(body: SuggestIn) -> JSONResponse:
    """Recognize wins in free text and return them as suggestions (not saved)."""
    text = (body.text or "").strip()
    if not text:
        return JSONResponse({"ok": False, "message": "Tell Neo about your day first."}, status_code=400)
    demo = not ANTHROPIC_KEY
    try:
        suggestions = _suggest_mock(text) if demo else _suggest_claude(text)
    except Exception as e:
        print(f"[wins] suggest failed: {e}")
        return JSONResponse({"ok": False, "message": "Couldn't read that — try again."}, status_code=502)
    return JSONResponse({"ok": True, "demo": demo, "suggestions": suggestions})


class AddIn(BaseModel):
    text: str
    category: str = "life"
    source: str = "manual"


@router.post("/api/wins/add")
async def add_win(body: AddIn) -> JSONResponse:
    """Save one win (a manual entry or a confirmed suggestion)."""
    text = (body.text or "").strip()
    if not text:
        return JSONResponse({"ok": False, "message": "Empty win."}, status_code=400)
    win = {
        "id": uuid.uuid4().hex[:8],
        "text": text,
        "category": _norm_cat(body.category),
        "date": date.today().isoformat(),
        "source": "ai" if body.source == "ai" else "manual",
    }
    data = _data()
    data["wins"].insert(0, win)
    store.save("wins", data)
    return JSONResponse({"ok": True, "win": win})


class DeleteIn(BaseModel):
    id: str


@router.post("/api/wins/delete")
async def delete_win(body: DeleteIn) -> JSONResponse:
    data = _data()
    before = len(data["wins"])
    data["wins"] = [w for w in data["wins"] if w.get("id") != body.id]
    store.save("wins", data)
    return JSONResponse({"ok": True, "removed": before - len(data["wins"])})


# ── Page ──────────────────────────────────────────────────────────────────────
@router.get("/wins", response_class=HTMLResponse)
async def wins_page() -> HTMLResponse:
    return HTMLResponse(theme.page("Wins", _BODY, active="wins"))


_BODY = r"""
<style>
  .w-head { margin-bottom: 6px; } .w-head h1 { font-size: 40px; } .w-head h1 b { color: var(--gold); font-weight: 400; }
  .sub { font-size: 12.5px; color: var(--muted); margin-bottom: 22px; }
  .teller { background: linear-gradient(180deg, var(--panel-2), var(--panel)); border: 1px solid var(--line); border-radius: 14px; padding: 16px; margin-bottom: 16px; }
  .teller .lbl { font-size: 12.5px; color: var(--muted); margin-bottom: 10px; }
  .teller .lbl b { color: var(--gold); }
  .teller-row { display: flex; gap: 10px; } .teller textarea { flex: 1; min-height: 46px; resize: none; }
  .suggests { margin-top: 14px; display: none; } .suggests.show { display: block; }
  .suggests .stitle { font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--gold); margin-bottom: 10px; display: flex; gap: 10px; align-items: center; }
  .sug { display: flex; align-items: center; gap: 10px; background: var(--field); border: 1px solid var(--line); border-radius: 10px; padding: 9px 12px; margin-bottom: 8px; }
  .sug .txt { flex: 1; font-size: 13.5px; }
  .sug.added { opacity: 0.5; }
  .quick { display: flex; gap: 8px; margin-bottom: 28px; }
  .quick input { flex: 1; }
  .tag { font-size: 9.5px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; border-radius: 20px; padding: 2px 9px; white-space: nowrap; }
  .tag.work { background: rgba(90,140,210,0.18); color: #8db4e8; }
  .tag.life { background: rgba(184,169,217,0.18); color: #c3b4e0; }
  .tag.health { background: rgba(110,190,140,0.18); color: #84d0a0; }
  .tag.build { background: var(--gold-soft); color: var(--gold); }
  .day { margin-bottom: 22px; }
  .day h2 { font-size: 15px; letter-spacing: 0.05em; color: var(--text); margin-bottom: 10px; }
  .day .count { font-size: 11px; color: var(--muted); font-weight: 400; }
  .win { display: flex; align-items: center; gap: 12px; background: var(--panel); border: 1px solid var(--line-soft); border-radius: 11px; padding: 12px 14px; margin-bottom: 8px; }
  .win .wtxt { flex: 1; font-size: 14px; }
  .win .ai { font-size: 11px; color: var(--gold); } .win .x { cursor: pointer; color: #56638a; font-size: 14px; background: none; border: none; }
  .win .x:hover { color: #d98a3a; }
  .empty { color: #56638a; font-style: italic; font-size: 13px; }
  .spin { display: inline-block; width: 12px; height: 12px; border: 2px solid #1a1305; border-right-color: transparent; border-radius: 50%; animation: sp 0.7s linear infinite; vertical-align: -1px; }
  @keyframes sp { to { transform: rotate(360deg); } }
</style>

<main>
  <div class="w-head"><h1>Daily <b>Wins</b></h1></div>
  <p class="sub">Log what went well. Tell Neo about your day and it spots the wins — you decide which to keep.</p>

  <div class="teller">
    <div class="lbl">How was your day? <b>e.g. “made that phone call, fixed the deploy bug, and went for a run”</b></div>
    <div class="teller-row">
      <textarea id="day-input" placeholder="Tell Neo about your day…"></textarea>
      <button class="btn btn-gold" id="find-btn">Find wins</button>
    </div>
    <div class="suggests" id="suggests"></div>
  </div>

  <div class="quick">
    <input id="quick-text" type="text" placeholder="…or log one win directly">
    <select id="quick-cat">
      <option value="work">work</option><option value="life">life</option>
      <option value="health">health</option><option value="build">build</option>
    </select>
    <button class="btn btn-sm" id="quick-add">Add</button>
  </div>

  <div id="list"></div>
</main>

<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])));
let wins = [];

function dayLabel(iso) {
  const today = new Date(); const d = new Date(iso + "T00:00:00");
  const diff = Math.round((today.setHours(0,0,0,0) - d.setHours(0,0,0,0)) / 86400000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  const m = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const p = iso.split("-"); return `${m[parseInt(p[1],10)-1]} ${parseInt(p[2],10)}, ${p[0]}`;
}
function winRow(w) {
  return `<div class="win">
    <span class="tag ${esc(w.category)}">${esc(w.category)}</span>
    <span class="wtxt">${esc(w.text)}</span>
    ${w.source === "ai" ? '<span class="ai" title="Recognized by Neo">✨</span>' : ""}
    <button class="x" data-id="${esc(w.id)}" title="Remove">✕</button>
  </div>`;
}
function render() {
  const list = $("#list");
  if (!wins.length) { list.innerHTML = '<div class="empty">No wins logged yet — tell Neo about your day above.</div>'; return; }
  const byDay = {};
  wins.forEach(w => { (byDay[w.date] = byDay[w.date] || []).push(w); });
  const days = Object.keys(byDay).sort().reverse();
  list.innerHTML = days.map(d => `
    <div class="day"><h2>${esc(dayLabel(d))} <span class="count">· ${byDay[d].length}</span></h2>
      ${byDay[d].map(winRow).join("")}</div>`).join("");
  list.querySelectorAll(".x").forEach(b => b.addEventListener("click", () => removeWin(b.dataset.id)));
}
async function load() { try { wins = (await (await fetch("/api/wins")).json()).wins || []; } catch (_) {} render(); }

async function postJSON(url, body) {
  return (await fetch(url, { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body) })).json();
}

// ── Recognize → confirm ──
$("#find-btn").addEventListener("click", async () => {
  const text = $("#day-input").value.trim();
  if (!text) return;
  const btn = $("#find-btn"), box = $("#suggests");
  btn.disabled = true; btn.innerHTML = '<span class="spin"></span>';
  try {
    const out = await postJSON("/api/wins/suggest", { text });
    if (!out.ok) { box.innerHTML = `<div class="empty">${esc(out.message||"Failed.")}</div>`; box.classList.add("show"); }
    else if (!out.suggestions.length) { box.innerHTML = '<div class="empty">No clear wins in that — try adding detail, or log one directly below.</div>'; box.classList.add("show"); }
    else {
      box.innerHTML = `<div class="stitle">Neo found ${out.suggestions.length} — add the ones you want
        <button class="btn btn-sm" id="add-all">Add all</button></div>` +
        out.suggestions.map((s,i) => `<div class="sug" data-i="${i}">
          <span class="tag ${esc(s.category)}">${esc(s.category)}</span>
          <span class="txt">${esc(s.text)}</span>
          <button class="btn btn-sm add-one" data-i="${i}">+ Add</button></div>`).join("");
      box.classList.add("show");
      box._sugs = out.suggestions;
      box.querySelectorAll(".add-one").forEach(b => b.addEventListener("click", () => addSuggestion(b.dataset.i)));
      $("#add-all").addEventListener("click", async () => {
        for (const el of box.querySelectorAll(".sug:not(.added)")) await addSuggestion(el.dataset.i);
      });
    }
  } catch (_) {}
  btn.disabled = false; btn.textContent = "Find wins";
});
async function addSuggestion(i) {
  const box = $("#suggests"); const s = box._sugs[i];
  const el = box.querySelector(`.sug[data-i="${i}"]`);
  if (!s || (el && el.classList.contains("added"))) return;
  const out = await postJSON("/api/wins/add", { text: s.text, category: s.category, source: "ai" });
  if (out.ok) { if (el) { el.classList.add("added"); el.querySelector(".add-one").textContent = "✓ Added"; } await load(); }
}

// ── Quick manual add ──
async function quickAdd() {
  const text = $("#quick-text").value.trim();
  if (!text) return;
  const out = await postJSON("/api/wins/add", { text, category: $("#quick-cat").value, source: "manual" });
  if (out.ok) { $("#quick-text").value = ""; await load(); }
}
$("#quick-add").addEventListener("click", quickAdd);
$("#quick-text").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); quickAdd(); } });

async function removeWin(id) { await postJSON("/api/wins/delete", { id }); await load(); }

load();
</script>
"""
