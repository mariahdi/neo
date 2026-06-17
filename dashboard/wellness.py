"""Wellness (NEO-44) — non-negotiables, routine, and life rules (Aria port).

A daily check-in over your non-negotiables (checked off per day), your weekly
routine, and the life rules worth re-reading. The check-in state is stored by
date so today's progress persists. A private-leaning module — no masking needed.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

from . import store, theme

router = APIRouter()

DEFAULT = {
    "nonneg": [
        {"id": "meds", "emoji": "💊", "label": "Take meds", "note": "Infrastructure. Non-negotiable."},
        {"id": "therapy", "emoji": "🛋", "label": "Therapy every 1-2 weeks", "note": "Keep going."},
        {"id": "volleyball", "emoji": "🏐", "label": "Volleyball Tuesdays", "note": "You always feel better after."},
        {"id": "outside", "emoji": "🚶🏾", "label": "Leave the apartment daily", "note": "Movement breaks the loop."},
        {"id": "sleep", "emoji": "🌙", "label": "Sleep with intention", "note": "Not perfect. Just not destroying it."},
        {"id": "cook", "emoji": "🍳", "label": "Cook once a week", "note": "Structure + saves money."},
        {"id": "joy", "emoji": "✨", "label": "Protect moments of joy", "note": "Don't shut the good moods down."},
    ],
    "routine": [
        {"time": "7:00am", "emoji": "⏰", "label": "Wake up", "note": "Alarm set. You made it."},
        {"time": "7:30am", "emoji": "💊", "label": "Meds", "note": "Before anything else."},
        {"time": "8:00am", "emoji": "🚇", "label": "Leave for metro", "note": "Leave by 8 or you're late."},
        {"time": "12:00pm", "emoji": "🥗", "label": "Lunch", "note": "Real food."},
        {"time": "4:30pm", "emoji": "🏠", "label": "Head home", "note": "Decompress. You did the day."},
        {"time": "10:30pm", "emoji": "😴", "label": "In bed", "note": "Phone down. Sleep is the unlock."},
    ],
    "rules": [
        {"emoji": "🛸", "rule": "You are the flight director of your own life. Act like it."},
        {"emoji": "🌅", "rule": "Finding reasons to live in moments of joy is valid and important."},
        {"emoji": "🧠", "rule": "Depression is biology, not character failure."},
        {"emoji": "🌿", "rule": "Weight changes on meds are expected. Be kind to your body."},
        {"emoji": "🕊", "rule": "You don't owe anyone an explanation for your rest or your joy."},
        {"emoji": "✦", "rule": "Statistically rare. Actually thriving. It's true."},
    ],
    "checks": {},
}


def _data() -> dict:
    return store.load("wellness", DEFAULT)


@router.get("/api/wellness")
async def get_wellness() -> JSONResponse:
    return JSONResponse(_data())


@router.post("/api/wellness/check")
async def toggle_check(body: dict) -> JSONResponse:
    """Toggle one non-negotiable for today."""
    d = _data()
    key = f"{date.today().isoformat()}-{body.get('id')}"
    checks = d.setdefault("checks", {})
    checks[key] = not checks.get(key, False)
    store.save("wellness", d)
    return JSONResponse(d)


@router.get("/wellness", response_class=HTMLResponse)
async def wellness_page() -> HTMLResponse:
    return HTMLResponse(theme.page("Wellness", _BODY, active="wellness"))


_BODY = r"""
<style>
  .we-head h1 { font-size: 40px; } .we-head h1 b { color: var(--gold); font-weight: 400; }
  .we-sub { font-size: 12.5px; color: var(--muted); margin: 2px 0 22px; }
  .sec { font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--gold); margin: 26px 0 12px; }
  .checkin { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 14px; padding: 20px; }
  .ci-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
  .ci-top .c { font-size: 13px; color: #80D4A0; }
  .ci-bar { height: 4px; background: var(--field); border-radius: 2px; overflow: hidden; margin-bottom: 18px; }
  .ci-bar > span { display: block; height: 100%; background: #80D4A0; transition: width 0.3s; }
  .nn { display: flex; align-items: flex-start; gap: 12px; cursor: pointer; padding: 7px 0; }
  .nn .box { width: 20px; height: 20px; border-radius: 6px; border: 2px solid var(--line); flex-shrink: 0; margin-top: 1px; display: flex; align-items: center; justify-content: center; font-size: 11px; }
  .nn.done .box { background: #80D4A0; border-color: #80D4A0; color: var(--bg); }
  .nn .nl { font-size: 14px; } .nn.done .nl { color: var(--muted); text-decoration: line-through; }
  .nn .nt { font-size: 11px; color: var(--muted); margin-top: 2px; }
  .rt { display: flex; align-items: center; gap: 14px; padding: 12px 16px; background: var(--panel); border: 1px solid var(--line-soft); border-left: 3px solid var(--gold); border-radius: 10px; margin-bottom: 8px; }
  .rt .rl { flex: 1; } .rt .rl .rlab { font-size: 13px; } .rt .rl .rnote { font-size: 10px; color: var(--muted); margin-top: 2px; }
  .rt .rtime { font-size: 11px; color: var(--gold); }
  .rule { display: flex; gap: 14px; align-items: flex-start; background: var(--panel); border: 1px solid var(--line-soft); border-radius: 12px; padding: 15px 18px; margin-bottom: 9px; border-left: 3px solid var(--gold-line); }
  .rule .rr { font-size: 14px; line-height: 1.6; }
</style>

<main>
  <div class="we-head"><h1>Wellness <b>🌸</b></h1></div>
  <p class="we-sub">your non-negotiables · your rules · your life</p>

  <div class="sec">Today's Check-in</div>
  <div class="checkin">
    <div class="ci-top"><span style="font-size:11px;letter-spacing:0.1em;color:var(--muted)">NON-NEGOTIABLES</span><span class="c" id="ci-count">0/0</span></div>
    <div class="ci-bar"><span id="ci-fill" style="width:0%"></span></div>
    <div id="nonneg"></div>
  </div>

  <div class="sec">Weekly Routine</div>
  <div id="routine"></div>

  <div class="sec">Life Rules</div>
  <div id="rules"></div>
</main>

<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])));
let data = { nonneg: [], routine: [], rules: [], checks: {} };
const today = new Date().toISOString().split("T")[0];
const isChecked = (id) => !!data.checks[`${today}-${id}`];

function render() {
  const done = data.nonneg.filter(n => isChecked(n.id)).length;
  $("#ci-count").textContent = `${done}/${data.nonneg.length}`;
  $("#ci-fill").style.width = (data.nonneg.length ? done / data.nonneg.length * 100 : 0) + "%";
  $("#nonneg").innerHTML = data.nonneg.map(n => `<div class="nn ${isChecked(n.id) ? "done" : ""}" data-id="${esc(n.id)}">
    <div class="box">${isChecked(n.id) ? "✓" : ""}</div>
    <div><div class="nl">${esc(n.emoji)} ${esc(n.label)}</div><div class="nt">${esc(n.note)}</div></div></div>`).join("");
  $("#nonneg").querySelectorAll("[data-id]").forEach(el => el.addEventListener("click", () => toggle(el.dataset.id)));
  $("#routine").innerHTML = data.routine.map(r => `<div class="rt">
    <span style="font-size:18px">${esc(r.emoji)}</span>
    <div class="rl"><div class="rlab">${esc(r.label)}</div><div class="rnote">${esc(r.note)}</div></div>
    <span class="rtime">${esc(r.time)}</span></div>`).join("");
  $("#rules").innerHTML = data.rules.map(r => `<div class="rule"><span style="font-size:20px">${esc(r.emoji)}</span><div class="rr">${esc(r.rule)}</div></div>`).join("");
}

async function toggle(id) {
  data = await (await fetch("/api/wellness/check", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ id }) })).json();
  render();
}

(async () => { try { data = await (await fetch("/api/wellness")).json(); } catch (_) {} render(); })();
</script>
"""
