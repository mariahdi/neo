"""Trips (NEO-43) — travel planner, ported from the Aria reference app.

Trips with a status, dates, flight details, a per-audience note, and a to-do
checklist. View-modes are first-class here: flight + confirmation are
Private-only, the note text changes per audience (you write a different line
for Friends vs Coworker vs Public), and each to-do declares which views it
shows in. State persists to the store.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

from . import store, theme

router = APIRouter()

DEFAULT = {
    "trips": [
        {"id": 1, "city": "Austin, TX", "emoji": "🤠", "status": "booked", "dates": "Aug 28–30, 2026",
         "flight": "UA 2337 · IAD→AUS · Aug 28\nUA 525 · AUS→IAD · Aug 30", "confirmation": "E1C3ZG",
         "notes": {"private": "Taylor's 26th birthday 🎂 — she asked you to come. One full day Aug 29.",
                   "friends": "Taylor's 26th birthday 🎂 in Austin!",
                   "coworker": "Traveling to Austin end of August.",
                   "public": "Trip coming up ✈️"},
         "todos": [{"id": 1, "text": "Confirm plans with Taylor 🎂", "done": False, "views": ["private", "friends"]},
                   {"id": 2, "text": "Book hotel / Airbnb", "done": False, "views": ["private", "friends"]},
                   {"id": 3, "text": "Get Taylor a birthday gift", "done": False, "views": ["private"]}]},
        {"id": 2, "city": "Arizona", "emoji": "🏜️", "status": "planning", "dates": "TBD",
         "flight": "", "confirmation": "",
         "notes": {"private": "Still planning — dates TBD.", "friends": "Planning an Arizona trip!",
                   "coworker": "Planning some travel.", "public": ""},
         "todos": [{"id": 1, "text": "Pick dates", "done": False, "views": ["private", "friends"]},
                   {"id": 2, "text": "Book flights", "done": False, "views": ["private", "friends"]}]},
        {"id": 3, "city": "New Orleans, LA", "emoji": "🎷", "status": "planning", "dates": "TBD",
         "flight": "", "confirmation": "",
         "notes": {"private": "NOLA deserves a proper trip.", "friends": "Planning NOLA 🎷",
                   "coworker": "Planning some travel.", "public": ""},
         "todos": [{"id": 1, "text": "Pick dates", "done": False, "views": ["private", "friends"]}]},
    ],
}


def _data() -> dict:
    return store.load("trips", DEFAULT)


@router.get("/api/trips")
async def get_trips() -> JSONResponse:
    return JSONResponse(_data())


@router.post("/api/trips")
async def save_trips(body: dict) -> JSONResponse:
    data = {"trips": body.get("trips", [])}
    store.save("trips", data)
    return JSONResponse(data)


@router.get("/trips", response_class=HTMLResponse)
async def trips_page() -> HTMLResponse:
    return HTMLResponse(theme.page("Trips", _BODY, active="trips"))


_BODY = r"""
<style>
  .t-head h1 { font-size: 40px; } .t-head h1 b { color: var(--gold); font-weight: 400; }
  .t-sub { font-size: 12.5px; color: var(--muted); margin: 2px 0 22px; }
  .trip { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 14px; margin-bottom: 14px; border-left: 3px solid var(--gold); overflow: hidden; }
  .trip-top { padding: 18px 20px; display: flex; align-items: center; justify-content: space-between; gap: 12px; cursor: pointer; }
  .trip-left { display: flex; align-items: center; gap: 14px; }
  .trip-city { font-size: 18px; } .trip-dates { font-size: 12px; color: var(--muted); margin-top: 2px; }
  .status { font-size: 11px; padding: 3px 10px; border-radius: 20px; white-space: nowrap; }
  .status.booked { color: #80D4A0; background: rgba(128,212,160,0.12); border: 1px solid rgba(128,212,160,0.4); }
  .status.planning { color: #F0D080; background: rgba(240,208,128,0.12); border: 1px solid rgba(240,208,128,0.4); }
  .trip-body { padding: 0 20px 20px; border-top: 1px solid var(--line-soft); }
  .flight { margin-top: 14px; padding: 12px 14px; background: var(--field); border-radius: 10px; }
  .flight .fl { font-size: 9px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--muted); margin-bottom: 6px; }
  .flight .fv { font-size: 12.5px; white-space: pre-line; line-height: 1.8; }
  .flight .cf { font-size: 11px; color: var(--gold); margin-top: 6px; }
  .note { font-size: 13px; color: var(--muted); margin-top: 14px; line-height: 1.6; }
  .todos { margin-top: 16px; }
  .todos .tl { font-size: 9px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--muted); margin-bottom: 10px; }
  .todo { display: flex; align-items: center; gap: 10px; cursor: pointer; padding: 5px 0; }
  .todo .box { width: 16px; height: 16px; border-radius: 50%; border: 2px solid var(--gold); flex-shrink: 0; }
  .todo.done .box { background: var(--gold); } .todo.done .tx { text-decoration: line-through; color: var(--muted); }
  .add { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 18px; }
  .add input.e { width: 48px; text-align: center; } .add input.c { flex: 1; min-width: 120px; } .add input.d { width: 130px; }
</style>

<main>
  <div class="t-head"><h1>Trips <b>✈️</b></h1></div>
  <p class="t-sub">where to next</p>
  <div id="trips"></div>
  <div class="add">
    <input class="e" id="a-emoji" type="text" value="📍">
    <input class="c" id="a-city" type="text" placeholder="City">
    <input class="d" id="a-dates" type="text" placeholder="Dates / TBD">
    <select id="a-status"><option value="planning">Planning</option><option value="booked">Booked</option></select>
    <button class="btn btn-gold btn-sm" id="a-btn">Add trip</button>
  </div>
</main>

<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])));
let data = { trips: [] };
let open = null;
const view = () => (window.neoView ? window.neoView() : "private");

function noteFor(t) {
  const n = t.notes || {};
  return n[view()] !== undefined && n[view()] !== "" ? n[view()] : (n.public || "");
}

function tripCard(t) {
  const isOpen = String(open) === String(t.id);
  const v = view();
  const todos = (t.todos || []).filter(td => (td.views || ["private"]).includes(v));
  const note = noteFor(t);
  return `<div class="trip">
    <div class="trip-top" data-open="${esc(String(t.id))}">
      <div class="trip-left"><span style="font-size:26px">${esc(t.emoji)}</span>
        <div><div class="trip-city">${esc(t.city)}</div><div class="trip-dates">${esc(t.dates)}</div></div></div>
      <div style="display:flex;align-items:center;gap:10px">
        <span class="status ${esc(t.status)}">${t.status === "booked" ? "✓ Booked" : "🗓️ Planning"}</span>
        <span style="color:var(--muted)">${isOpen ? "▲" : "▼"}</span></div>
    </div>
    ${isOpen ? `<div class="trip-body">
      ${(t.flight && v === "private") ? `<div class="flight"><div class="fl">Flight</div><div class="fv">${esc(t.flight)}</div>${t.confirmation ? `<div class="cf">Confirmation: ${esc(t.confirmation)}</div>` : ""}</div>` : ""}
      ${note ? `<div class="note">${esc(note)}</div>` : ""}
      ${todos.length ? `<div class="todos"><div class="tl">To-do</div>${todos.map(td => `
        <div class="todo ${td.done ? "done" : ""}" data-trip="${esc(String(t.id))}" data-todo="${esc(String(td.id))}">
          <div class="box"></div><span class="tx">${esc(td.text)}</span></div>`).join("")}</div>` : ""}
      <div style="margin-top:14px"><span class="btn btn-sm rm" data-rm="${esc(String(t.id))}" style="color:#F08080">🗑 remove trip</span></div>
    </div>` : ""}
  </div>`;
}

function render() {
  $("#trips").innerHTML = data.trips.map(tripCard).join("") || '<div style="color:var(--muted);font-style:italic">No trips yet — add one below.</div>';
  $("#trips").querySelectorAll("[data-open]").forEach(el => el.addEventListener("click", () => {
    open = String(open) === el.dataset.open ? null : el.dataset.open; render();
  }));
  $("#trips").querySelectorAll("[data-todo]").forEach(el => el.addEventListener("click", () => {
    const t = data.trips.find(x => String(x.id) === el.dataset.trip);
    const td = t && t.todos.find(x => String(x.id) === el.dataset.todo);
    if (td) { td.done = !td.done; save(); }
  }));
  $("#trips").querySelectorAll("[data-rm]").forEach(el => el.addEventListener("click", () => {
    data.trips = data.trips.filter(x => String(x.id) !== el.dataset.rm); save();
  }));
}

async function save() {
  data = await (await fetch("/api/trips", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(data) })).json();
  render();
}

$("#a-btn").addEventListener("click", () => {
  const city = $("#a-city").value.trim(); if (!city) return;
  data.trips.push({ id: Date.now(), city, emoji: $("#a-emoji").value.trim() || "📍", status: $("#a-status").value,
    dates: $("#a-dates").value.trim() || "TBD", flight: "", confirmation: "",
    notes: { private: "", friends: "", coworker: "", public: "" }, todos: [] });
  $("#a-city").value = ""; $("#a-dates").value = ""; $("#a-emoji").value = "📍"; save();
});

// Notes + flight + to-dos change with the audience — re-render on view change.
window.addEventListener("neo:view", render);

(async () => { try { data = await (await fetch("/api/trips")).json(); } catch (_) {} render(); })();
</script>
"""
