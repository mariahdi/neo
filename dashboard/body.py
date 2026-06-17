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

# Blank template — each instance fills its own health data.
DEFAULT = {
    "meds": [],
    "weight": {"current": 0, "target": 0, "history": []},
    "habits": [],
}


def _data() -> dict:
    return store.load("body", DEFAULT)


@router.get("/api/body")
async def get_body() -> JSONResponse:
    return JSONResponse(_data())


@router.post("/api/body")
async def save_body(body: dict) -> JSONResponse:
    """Full-state save (so lists can be cleared, target set, etc.)."""
    w = body.get("weight") or {}
    data = {
        "meds": [{"name": (m.get("name") or "").strip(),
                  "dose": (m.get("dose") or "—").strip(),
                  "time": (m.get("time") or "").strip()}
                 for m in body.get("meds", []) if (m.get("name") or "").strip()],
        "weight": {
            "current": round(float(w.get("current", 0) or 0)),
            "target": round(float(w.get("target", 0) or 0)),
            "history": w.get("history") if isinstance(w.get("history"), list) else [],
        },
        "habits": [{"icon": (h.get("icon") or "•").strip(),
                    "label": (h.get("label") or "").strip(),
                    "freq": (h.get("freq") or "").strip()}
                   for h in body.get("habits", []) if (h.get("label") or "").strip()],
    }
    store.save("body", data)
    return JSONResponse(data)


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
  .habit .ic { font-size: 22px; } .habit .hl { font-size: 13px; } .habit .hf { font-size: 10px; color: var(--muted); margin-top: 3px; }
  .spark { display: block; margin-top: 8px; }
  .addrow { display: flex; gap: 8px; margin: 10px 0 4px; flex-wrap: wrap; }
  .addrow input { flex: 1; min-width: 90px; }
  .x { background: none; border: none; color: var(--muted); cursor: pointer; font-size: 13px; }
  .x:hover { color: #F08080; }
  .empty { color: var(--muted); font-style: italic; font-size: 13px; padding: 4px 0; }
</style>

<main>
  <div class="body-head"><h1>Body <b>🫀</b></h1></div>

  <div class="sec-label">Medications</div>
  <div id="meds"></div>
  <div class="addrow">
    <input id="m-name" type="text" placeholder="Medication">
    <input id="m-dose" type="text" placeholder="Dose" style="flex:0 0 80px;min-width:0">
    <input id="m-time" type="text" placeholder="When" style="flex:0 0 100px;min-width:0">
    <button class="btn btn-gold btn-sm" id="m-add">Add</button>
  </div>

  <div class="sec-label">Weight Journey</div>
  <div class="wt">
    <div class="wt-row">
      <div><div class="lab">Now</div><div class="v" style="color:#F08080" id="w-now">—</div></div>
      <div style="text-align:center"><div class="lab">To lose</div><div class="v" style="color:var(--gold)" id="w-lose">—</div></div>
      <div style="text-align:right"><div class="lab">Target</div><input type="number" id="w-target" placeholder="—" style="width:78px;text-align:right;font-size:20px;font-weight:700;color:#80D4A0;padding:4px 6px"></div>
    </div>
    <div id="w-chart"></div>
    <div class="weigh">
      <input type="number" id="weigh-input" placeholder="Log today's weight">
      <button class="btn btn-gold btn-sm" id="weigh-btn">Log</button>
    </div>
  </div>

  <div class="sec-label">Weekly Habits</div>
  <div class="habits" id="habits"></div>
  <div class="addrow">
    <input id="h-icon" type="text" value="✅" style="flex:0 0 48px;min-width:0;text-align:center">
    <input id="h-label" type="text" placeholder="Habit">
    <input id="h-freq" type="text" placeholder="How often" style="flex:0 0 120px;min-width:0">
    <button class="btn btn-gold btn-sm" id="h-add">Add</button>
  </div>
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
  $("#meds").innerHTML = data.meds.length ? data.meds.map((m, i) => `<div class="med">
    <div><div class="nm">${esc(m.name)}</div><div class="tm">${esc(m.time)}</div></div>
    <div style="display:flex;align-items:center;gap:12px"><div class="ds">${esc(m.dose)}</div><button class="x" data-rm-med="${i}">✕</button></div></div>`).join("")
    : '<div class="empty">No meds yet — add one below.</div>';

  const w = data.weight || {};
  const lose = Math.max(0, (Number(w.current)||0) - (Number(w.target)||0));
  $("#w-now").textContent = w.current || "—";
  $("#w-lose").textContent = lose || "—";
  if (document.activeElement !== $("#w-target")) $("#w-target").value = w.target || "";
  $("#w-chart").innerHTML = sparkline(w.history);

  $("#habits").innerHTML = (data.habits || []).length ? data.habits.map((h, i) => `<div class="habit">
    <div style="display:flex;justify-content:space-between;align-items:flex-start"><div class="ic">${esc(h.icon)}</div><button class="x" data-rm-habit="${i}">✕</button></div>
    <div class="hl">${esc(h.label)}</div><div class="hf">${esc(h.freq)}</div></div>`).join("")
    : '<div class="empty">No habits yet — add one below.</div>';

  document.querySelectorAll("[data-rm-med]").forEach(b => b.addEventListener("click", () => { data.meds.splice(+b.dataset.rmMed, 1); save(); }));
  document.querySelectorAll("[data-rm-habit]").forEach(b => b.addEventListener("click", () => { data.habits.splice(+b.dataset.rmHabit, 1); save(); }));
}

async function save() { data = await (await fetch("/api/body", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(data) })).json(); render(); }
async function load() { try { data = await (await fetch("/api/body")).json(); } catch (_) {} render(); }

$("#weigh-btn").addEventListener("click", async () => {
  const v = parseFloat($("#weigh-input").value); if (isNaN(v)) return;
  data = await (await fetch("/api/body/weigh", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ value: v }) })).json();
  $("#weigh-input").value = ""; render();
});
$("#w-target").addEventListener("change", () => { data.weight.target = Math.max(0, parseInt($("#w-target").value) || 0); save(); });
$("#m-add").addEventListener("click", () => {
  const name = $("#m-name").value.trim(); if (!name) return;
  data.meds.push({ name, dose: $("#m-dose").value.trim() || "—", time: $("#m-time").value.trim() });
  $("#m-name").value = ""; $("#m-dose").value = ""; $("#m-time").value = ""; save();
});
$("#h-add").addEventListener("click", () => {
  const label = $("#h-label").value.trim(); if (!label) return;
  data.habits.push({ icon: $("#h-icon").value.trim() || "✅", label, freq: $("#h-freq").value.trim() });
  $("#h-label").value = ""; $("#h-freq").value = ""; $("#h-icon").value = "✅"; save();
});
load();
</script>
"""
