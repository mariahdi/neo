"""Goals (NEO-31) — personal goal tracking with a Claude intelligence layer.

Goals live in categories (financial, fitness, learning, project, …), each with
a start / current / target value and a history of entries over time, so you can
see progress build. Structure persists to the JSON store.

The intelligence layer: a "Tell Neo an update" box takes natural language —
"weighed myself this morning, 182" — and a live Anthropic call figures out
which goal it's about and the new value, then logs it. The call returns strict
JSON so the rest of the app stays dumb; a keyword/number heuristic stands in
when no Anthropic key is set, so the feature still demos offline.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date

import requests
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from . import store, theme

router = APIRouter()

ANTHROPIC_KEY = os.environ.get("NEO_ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.environ.get("NEO_ANTHROPIC_MODEL", "claude-sonnet-4-6")

CATEGORIES = ["financial", "fitness", "learning", "project"]

# Seed goals (mock until edited). `start`/`current`/`target` drive the bar.
DEFAULT = {
    "goals": [
        {"id": "weight", "title": "Get to 175 lbs", "category": "fitness", "unit": "lbs",
         "start": 190, "current": 182, "target": 175,
         "history": [{"date": "2026-06-01", "value": 190, "note": "starting point"},
                     {"date": "2026-06-15", "value": 182, "note": ""}]},
        {"id": "fund", "title": "Save $10,000 emergency fund", "category": "financial", "unit": "$",
         "start": 0, "current": 3500, "target": 10000,
         "history": [{"date": "2026-05-01", "value": 0, "note": ""},
                     {"date": "2026-06-10", "value": 3500, "note": ""}]},
        {"id": "books", "title": "Read 12 books this year", "category": "learning", "unit": "books",
         "start": 0, "current": 4, "target": 12,
         "history": [{"date": "2026-06-12", "value": 4, "note": ""}]},
        {"id": "neo", "title": "Ship NEO v1", "category": "project", "unit": "%",
         "start": 0, "current": 60, "target": 100,
         "history": [{"date": "2026-06-16", "value": 60, "note": "dashboard live"}]},
    ],
}


def _data() -> dict:
    return store.load("goals", DEFAULT)


def _num(v: float):
    """Whole numbers as ints (182.0 -> 182), else leave as-is."""
    try:
        f = float(v)
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return v


# ── Intelligence layer ────────────────────────────────────────────────────────
def _infer_claude(text: str, goals: list[dict]) -> dict:
    """Ask Claude which goal a free-text update is about + the new value.
    Returns {matched, goal_id?, value?, note?, message?}."""
    brief = [{"id": g["id"], "title": g["title"], "category": g["category"],
              "unit": g["unit"], "current": g["current"]} for g in goals]
    prompt = (
        "You maintain a personal goals tracker. Current goals (JSON):\n"
        f"{json.dumps(brief)}\n\n"
        f'The user said: "{text}"\n\n'
        "Decide if this reports progress on exactly ONE goal. Reply with ONLY a "
        "JSON object, no prose:\n"
        '{"matched": true, "goal_id": "<id>", "value": <number — the NEW current '
        'value in that goal\'s unit>, "note": "<short note or empty>"}\n'
        "or\n"
        '{"matched": false, "message": "<one short sentence on why nothing matched>"}\n'
        "If the user gives a delta (e.g. 'read 2 more books'), add it to that "
        "goal's current value. value must be a plain number."
    )
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": ANTHROPIC_MODEL, "max_tokens": 300,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=40,
    )
    resp.raise_for_status()
    raw = resp.json()["content"][0]["text"].strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        raw = raw[4:] if raw.startswith("json") else raw
    return json.loads(raw.strip())


def _infer_mock(text: str, goals: list[dict]) -> dict:
    """Offline stand-in: pull the last number and match a goal by keyword."""
    nums = re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    if not nums:
        return {"matched": False, "message": "I couldn't find a number in that."}
    value = _num(nums[-1])
    low = text.lower()
    for g in goals:
        keys = set(re.findall(r"[a-z]+", g["title"].lower())) | {g["category"], g["unit"].lower()}
        if "lbs" in g["unit"].lower() or "weight" in g["title"].lower():
            keys |= {"weigh", "weighed", "weight", "pounds"}
        if any(k and len(k) > 2 and k in low for k in keys):
            return {"matched": True, "goal_id": g["id"], "value": value,
                    "note": "(logged offline — set the Anthropic key for smarter parsing)"}
    return {"matched": False, "message": "I couldn't tell which goal that's about."}


# ── API ───────────────────────────────────────────────────────────────────────
@router.get("/api/goals")
async def get_goals() -> JSONResponse:
    return JSONResponse(_data())


class GoalsIn(BaseModel):
    goals: list[dict] = []


@router.post("/api/goals")
async def save_goals(body: GoalsIn) -> JSONResponse:
    """Replace the goals structure (add/edit/remove). Histories ride along."""
    clean = []
    for g in body.goals:
        title = (g.get("title") or "").strip()
        if not title:
            continue
        clean.append({
            "id": (g.get("id") or re.sub(r"[^a-z0-9]+", "-", title.lower())[:24] or "goal"),
            "title": title,
            "category": (g.get("category") or "project").strip().lower(),
            "unit": (g.get("unit") or "").strip(),
            "start": _num(g.get("start", 0)),
            "current": _num(g.get("current", 0)),
            "target": _num(g.get("target", 0)),
            "history": g.get("history") or [],
        })
    data = {"goals": clean}
    store.save("goals", data)
    return JSONResponse(data)


class LogIn(BaseModel):
    text: str


@router.post("/api/goals/log")
async def log_update(body: LogIn) -> JSONResponse:
    """Natural-language progress update -> infer goal + value -> log it."""
    text = (body.text or "").strip()
    if not text:
        return JSONResponse({"ok": False, "message": "Type an update first."}, status_code=400)

    data = _data()
    goals = data["goals"]
    demo = not ANTHROPIC_KEY
    try:
        result = _infer_mock(text, goals) if demo else _infer_claude(text, goals)
    except Exception as e:
        print(f"[goals] inference failed: {e}")
        return JSONResponse({"ok": False, "message": "Couldn't read that update — try again."}, status_code=502)

    if not result.get("matched"):
        return JSONResponse({"ok": True, "matched": False, "demo": demo,
                             "message": result.get("message") or "Nothing matched."})

    gid = result.get("goal_id")
    value = _num(result.get("value"))
    note = (result.get("note") or "").strip()
    goal = next((g for g in goals if g["id"] == gid), None)
    if goal is None or value is None:
        return JSONResponse({"ok": True, "matched": False, "demo": demo,
                             "message": "I couldn't apply that update."})

    goal["current"] = value
    goal["history"].append({"date": date.today().isoformat(), "value": value, "note": note})
    store.save("goals", data)
    return JSONResponse({"ok": True, "matched": True, "demo": demo, "goal": goal,
                         "message": f"Logged {value} {goal['unit']} on “{goal['title']}.”"})


# ── Page ──────────────────────────────────────────────────────────────────────
@router.get("/goals", response_class=HTMLResponse)
async def goals_page() -> HTMLResponse:
    return HTMLResponse(theme.page("Goals", _BODY, active="goals"))


_BODY = r"""
<style>
  .g-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 18px; }
  .g-head h1 { font-size: 40px; } .g-head h1 b { color: var(--gold); font-weight: 400; }
  .teller { background: linear-gradient(180deg, var(--panel-2), var(--panel)); border: 1px solid var(--line); border-radius: 14px; padding: 16px; margin-bottom: 26px; }
  .teller .lbl { font-size: 12.5px; color: var(--muted); margin-bottom: 10px; }
  .teller .lbl b { color: var(--gold); }
  .teller-row { display: flex; gap: 10px; }
  .teller textarea { flex: 1; min-height: 44px; resize: none; }
  #log-reply { display: none; margin-top: 12px; font-size: 13px; padding: 10px 12px; border-radius: 9px; background: var(--gold-soft); border: 1px solid var(--gold-line); color: #f0e6c8; }
  #log-reply.show { display: block; } #log-reply.miss { background: rgba(135,148,179,0.1); border-color: var(--line); color: var(--muted); }
  .cat { margin-bottom: 24px; }
  .cat h2 { font-size: 18px; letter-spacing: 0.06em; text-transform: capitalize; color: var(--text); margin-bottom: 12px; }
  .goals-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; }
  .goal { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 12px; padding: 16px; }
  .goal-top { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
  .goal-title { font-size: 14.5px; font-weight: 700; }
  .goal-pct { font-size: 13px; color: var(--gold); font-weight: 700; }
  .bar { height: 8px; border-radius: 6px; background: #0c1322; border: 1px solid var(--line-soft); overflow: hidden; margin: 11px 0 8px; }
  .bar > span { display: block; height: 100%; background: var(--gold); border-radius: 6px; }
  .goal-meta { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-size: 12px; color: var(--muted); }
  .spark { display: block; margin-top: 10px; }
  .empty { color: #56638a; font-style: italic; font-size: 13px; }
  .mrow { display: grid; grid-template-columns: 1.6fr 1fr 0.8fr 0.8fr 0.8fr 0.8fr auto; gap: 7px; margin-bottom: 8px; align-items: center; }
  .mrow input, .mrow select { font-size: 12.5px; padding: 7px 8px; }
  .mhdr { font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); }
  .actions { display: flex; gap: 10px; margin-top: 10px; }
  .spin { display: inline-block; width: 12px; height: 12px; border: 2px solid #1a1305; border-right-color: transparent; border-radius: 50%; animation: sp 0.7s linear infinite; vertical-align: -1px; }
  @keyframes sp { to { transform: rotate(360deg); } }
</style>

<main>
  <div class="g-head"><h1>My <b>Goals</b></h1><button class="btn btn-sm" id="manage-btn">Manage</button></div>

  <div class="teller">
    <div class="lbl">Tell Neo an update — it figures out the goal. <b>e.g. “weighed myself this morning, 182”</b></div>
    <div class="teller-row">
      <textarea id="log-input" placeholder="What happened?"></textarea>
      <button class="btn btn-gold" id="log-btn">Log it</button>
    </div>
    <div id="log-reply"></div>
  </div>

  <div id="view"></div>

  <div id="manage" style="display:none;">
    <div class="mrow mhdr"><span>Title</span><span>Category</span><span>Unit</span><span>Start</span><span>Now</span><span>Target</span><span></span></div>
    <div id="mrows"></div>
    <button class="btn btn-sm" id="add-goal">+ Add goal</button>
    <div class="actions">
      <button class="btn btn-gold btn-sm" id="save-manage">Save changes</button>
      <button class="btn btn-sm" id="cancel-manage">Cancel</button>
    </div>
  </div>
</main>

<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])));
const CATS = ["financial","fitness","learning","project"];
let data = { goals: [] };

function pct(g) {
  const span = (g.target - g.start);
  if (!span) return g.current >= g.target ? 100 : 0;
  return Math.max(0, Math.min(100, Math.round((g.current - g.start) / span * 100)));
}
function sparkline(history) {
  const vals = (history || []).map(h => Number(h.value)).filter(v => !isNaN(v));
  if (vals.length < 2) return "";
  const w = 120, h = 30, min = Math.min(...vals), max = Math.max(...vals), rng = (max - min) || 1;
  const pts = vals.map((v, i) => `${(i/(vals.length-1)*w).toFixed(1)},${(h - (v-min)/rng*h).toFixed(1)}`).join(" ");
  return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline points="${pts}" fill="none" stroke="var(--gold)" stroke-width="1.5" stroke-linejoin="round"/></svg>`;
}
function goalCard(g) {
  return `<div class="goal">
    <div class="goal-top"><span class="goal-title">${esc(g.title)}</span><span class="goal-pct">${pct(g)}%</span></div>
    <div class="bar"><span style="width:${pct(g)}%"></span></div>
    <div class="goal-meta"><span>${esc(String(g.current))} / ${esc(String(g.target))} ${esc(g.unit)}</span>
      <span>${g.history && g.history.length ? esc(g.history[g.history.length-1].date) : ""}</span></div>
    ${sparkline(g.history)}
  </div>`;
}
function render() {
  const v = $("#view");
  const cats = [...new Set([...CATS, ...data.goals.map(g => g.category)])].filter(c => data.goals.some(g => g.category === c));
  if (!data.goals.length) { v.innerHTML = '<div class="empty">No goals yet — use Manage to add one.</div>'; return; }
  v.innerHTML = cats.map(c => `
    <div class="cat"><h2>${esc(c)}</h2>
      <div class="goals-grid">${data.goals.filter(g => g.category === c).map(goalCard).join("")}</div>
    </div>`).join("");
}
async function load() { try { data = await (await fetch("/api/goals")).json(); } catch (_) {} render(); }

// ── Tell Neo ──
async function logUpdate() {
  const text = $("#log-input").value.trim();
  if (!text) return;
  const btn = $("#log-btn"), reply = $("#log-reply");
  btn.disabled = true; btn.innerHTML = '<span class="spin"></span>';
  try {
    const out = await (await fetch("/api/goals/log", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ text }) })).json();
    reply.textContent = out.message || (out.ok ? "Done." : "Something went wrong.");
    reply.classList.add("show"); reply.classList.toggle("miss", !out.matched);
    if (out.matched) { $("#log-input").value = ""; await load(); }
  } catch (_) { reply.textContent = "Network error."; reply.classList.add("show","miss"); }
  btn.disabled = false; btn.textContent = "Log it";
}
$("#log-btn").addEventListener("click", logUpdate);
$("#log-input").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); logUpdate(); } });

// ── Manage ──
function goalRow(g = {title:"",category:"project",unit:"",start:0,current:0,target:0,history:[]}) {
  const row = document.createElement("div");
  row.className = "mrow";
  const opts = CATS.map(c => `<option ${c===g.category?"selected":""}>${c}</option>`).join("");
  row.innerHTML = `<input class="t" type="text" placeholder="Goal" value="${esc(g.title)}">
    <select class="c">${opts}</select>
    <input class="u" type="text" placeholder="unit" value="${esc(g.unit)}">
    <input class="s" type="text" value="${esc(String(g.start))}">
    <input class="n" type="text" value="${esc(String(g.current))}">
    <input class="g" type="text" value="${esc(String(g.target))}">
    <button class="btn btn-sm" type="button">✕</button>`;
  row.dataset.id = g.id || ""; row._history = g.history || [];
  row.querySelector("button").addEventListener("click", () => row.remove());
  return row;
}
$("#manage-btn").addEventListener("click", () => {
  const c = $("#mrows"); c.innerHTML = "";
  data.goals.forEach(g => c.appendChild(goalRow(g)));
  $("#view").style.display = "none"; $("#manage").style.display = "block"; $("#manage-btn").style.display = "none";
});
function closeManage(){ $("#view").style.display="block"; $("#manage").style.display="none"; $("#manage-btn").style.display="inline-block"; }
$("#cancel-manage").addEventListener("click", closeManage);
$("#add-goal").addEventListener("click", () => $("#mrows").appendChild(goalRow()));
$("#save-manage").addEventListener("click", async () => {
  const num = (s) => { const n = Number(s); return isNaN(n) ? 0 : n; };
  const goals = [...document.querySelectorAll("#mrows .mrow")].map(r => ({
    id: r.dataset.id,
    title: r.querySelector(".t").value.trim(),
    category: r.querySelector(".c").value,
    unit: r.querySelector(".u").value.trim(),
    start: num(r.querySelector(".s").value),
    current: num(r.querySelector(".n").value),
    target: num(r.querySelector(".g").value),
    history: r._history || [],
  })).filter(g => g.title);
  data = await (await fetch("/api/goals", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ goals }) })).json();
  render(); closeManage();
});

load();
</script>
"""
