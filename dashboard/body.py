"""Body (NEO-40) — health module, ported from the Aria reference app.

Medications, a weight journey (with history + a "log weight" box), and weekly
habits. The sensitive parts (meds + the weight chart) are gated to the Private
audience view via data-views, and the weight numbers go through the masking
engine — so Friends/Coworker/Public don't see your health data. State persists
to the store.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from . import store, theme

router = APIRouter()

DEFAULT = {
    "meds": [
        {"name": "Prozac", "dose": "80mg", "time": "morning"},
        {"name": "Abilify", "dose": "5mg", "time": "morning"},
        {"name": "Vitamin D3", "dose": "—", "time": "morning"},
        {"name": "Lo Loestrin", "dose": "—", "time": "daily"},
    ],
    "weight": {
        "current": 265, "target": 230,
        "history": [
            {"date": "2026-04-01", "value": 230},
            {"date": "2026-05-01", "value": 250},
            {"date": "2026-06-01", "value": 265},
        ],
    },
    "habits": [
        {"icon": "🏐", "label": "Sand Volleyball", "freq": "Tuesdays"},
        {"icon": "🚶🏾", "label": "Metro Walk", "freq": "Daily ~10min"},
        {"icon": "🧠", "label": "Therapy", "freq": "Every 1-2 wks"},
        {"icon": "🍳", "label": "Cook at home", "freq": "Goal: 1x/week"},
    ],
}


def _data() -> dict:
    return store.load("body", DEFAULT)


@router.get("/api/body")
async def get_body() -> JSONResponse:
    return JSONResponse(_data())


class BodyIn(BaseModel):
    meds: list[dict] = []
    weight: dict = {}
    habits: list[dict] = []


@router.post("/api/body")
async def save_body(body: BodyIn) -> JSONResponse:
    d = _data()
    if body.meds:
        d["meds"] = [{"name": (m.get("name") or "").strip(),
                      "dose": (m.get("dose") or "—").strip(),
                      "time": (m.get("time") or "").strip()}
                     for m in body.meds if (m.get("name") or "").strip()]
    if body.weight:
        w = d["weight"]
        w["current"] = body.weight.get("current", w["current"])
        w["target"] = body.weight.get("target", w["target"])
        if isinstance(body.weight.get("history"), list):
            w["history"] = body.weight["history"]
    if body.habits:
        d["habits"] = body.habits
    store.save("body", d)
    return JSONResponse(d)


class WeighIn(BaseModel):
    value: float


@router.post("/api/body/weigh")
async def log_weight(body: WeighIn) -> JSONResponse:
    d = _data()
    v = round(float(body.value))
    d["weight"]["current"] = v
    d["weight"].setdefault("history", []).append({"date": date.today().isoformat(), "value": v})
    store.save("body", d)
    return JSONResponse(d)


@router.get("/body", response_class=HTMLResponse)
async def body_page() -> HTMLResponse:
    return HTMLResponse(theme.page("Body", _BODY, active="body"))


_BODY = r"""
<style>
  .body-head h1 { font-size: 40px; } .body-head h1 b { color: var(--gold); font-weight: 400; }
  .sec-label { font-size: 9px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--muted); margin: 24px 0 10px; }
  .med { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 12px; padding: 13px 16px; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; border-left: 3px solid var(--gold); }
  .med .nm { font-size: 15px; } .med .tm { font-size: 11px; color: var(--muted); } .med .ds { font-size: 13px; color: var(--gold); }
  .private-note { background: var(--panel); border: 1px dashed var(--line); border-radius: 12px; padding: 20px; text-align: center; color: var(--muted); font-size: 13px; }
  .wt { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 14px; padding: 20px; margin-bottom: 10px; }
  .wt-row { display: flex; justify-content: space-between; margin-bottom: 14px; }
  .wt-row .lab { font-size: 10px; color: var(--muted); } .wt-row .v { font-size: 26px; font-weight: 700; }
  .weigh { display: flex; gap: 8px; margin-top: 12px; }
  .weigh input { flex: 1; }
  .note { font-size: 11px; color: var(--muted); margin-top: 10px; line-height: 1.6; }
  .habits { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .habit { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 12px; padding: 15px; border-top: 2px solid var(--gold); }
  .habit .ic { font-size: 22px; margin-bottom: 8px; } .habit .hl { font-size: 13px; } .habit .hf { font-size: 10px; color: var(--muted); margin-top: 3px; }
  .spark { display: block; margin-top: 8px; }
</style>

<main>
  <div class="body-head"><h1>Body <b>🫀</b></h1></div>

  <div class="sec-label">Medications</div>
  <div data-views="private" id="meds"></div>
  <div data-views="friends coworker public" class="private-note">🔒 Medications are private.</div>

  <div class="sec-label">Weight Journey</div>
  <div class="wt">
    <div class="wt-row">
      <div><div class="lab">Now</div><div class="v" style="color:#F08080"><span class="mask" data-type="text" id="w-now">—</span></div></div>
      <div style="text-align:center"><div class="lab">To lose</div><div class="v" style="color:var(--gold)"><span class="mask" data-type="text" id="w-lose">—</span></div></div>
      <div style="text-align:right"><div class="lab">Target</div><div class="v" style="color:#80D4A0"><span class="mask" data-type="text" id="w-target">—</span></div></div>
    </div>
    <div data-views="private">
      <div id="w-chart"></div>
      <div class="weigh">
        <input type="number" id="weigh-input" placeholder="Log today's weight">
        <button class="btn btn-gold btn-sm" id="weigh-btn">Log</button>
      </div>
    </div>
    <div data-views="friends coworker public" class="private-note">🔒 Weight history is private.</div>
    <div class="note">Prozac + Abilify can affect weight. This is biology, not willpower. 🤍</div>
  </div>

  <div class="sec-label">Weekly Habits</div>
  <div class="habits" id="habits"></div>
</main>

<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])));
let data = { meds: [], weight: { current: 0, target: 0, history: [] }, habits: [] };

function sparkline(history) {
  const vals = (history || []).map(h => Number(h.value)).filter(v => !isNaN(v));
  if (vals.length < 2) return "";
  const w = 280, h = 70, min = Math.min(...vals), max = Math.max(...vals), rng = (max - min) || 1;
  const pts = vals.map((v, i) => `${(i/(vals.length-1)*w).toFixed(1)},${(h - (v-min)/rng*h).toFixed(1)}`).join(" ");
  return `<svg class="spark" width="100%" height="${h}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><polyline points="${pts}" fill="none" stroke="var(--gold)" stroke-width="2"/></svg>`;
}

function render() {
  $("#meds").innerHTML = data.meds.map(m => `<div class="med">
    <div><div class="nm">${esc(m.name)}</div><div class="tm">${esc(m.time)}</div></div>
    <div class="ds">${esc(m.dose)}</div></div>`).join("") || '<div class="private-note">No meds logged.</div>';

  const w = data.weight || {};
  const lose = Math.max(0, (Number(w.current)||0) - (Number(w.target)||0));
  $("#w-now").dataset.real = w.current; $("#w-now").textContent = w.current;
  $("#w-lose").dataset.real = lose; $("#w-lose").textContent = lose;
  $("#w-target").dataset.real = w.target; $("#w-target").textContent = w.target;
  $("#w-chart").innerHTML = sparkline(w.history);

  $("#habits").innerHTML = (data.habits || []).map(h => `<div class="habit">
    <div class="ic">${esc(h.icon)}</div><div class="hl">${esc(h.label)}</div><div class="hf">${esc(h.freq)}</div></div>`).join("");

  if (window.neoMaskScan) window.neoMaskScan();
}

async function load() { try { data = await (await fetch("/api/body")).json(); } catch (_) {} render(); }

$("#weigh-btn").addEventListener("click", async () => {
  const v = parseFloat($("#weigh-input").value); if (isNaN(v)) return;
  data = await (await fetch("/api/body/weigh", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ value: v }) })).json();
  $("#weigh-input").value = ""; render();
});

window.addEventListener("neo:view", () => { if (window.neoMaskScan) window.neoMaskScan(); });
load();
</script>
"""
