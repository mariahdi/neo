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

# Gentle sample entries — shown for inspiration until you make it your own
# (saving your own list replaces them). Kept calm and non-clinical on purpose.
DEFAULT = {
    "nonneg": [
        {"id": "n0", "emoji": "💧", "label": "Drink water", "note": "A glass when you wake up"},
        {"id": "n1", "emoji": "🌿", "label": "Step outside", "note": "Even five minutes counts"},
        {"id": "n2", "emoji": "😴", "label": "Wind down screen-free", "note": "20 min before bed"},
    ],
    "routine": [
        {"time": "Morning", "emoji": "☀️", "label": "Slow start", "note": "Water, light, a few breaths"},
        {"time": "Midday", "emoji": "🥪", "label": "Real break", "note": "Step away to eat"},
        {"time": "Evening", "emoji": "🌙", "label": "Wind down", "note": "Dim the lights, ease off"},
    ],
    "rules": [
        {"emoji": "🌱", "rule": "Progress over perfection."},
        {"emoji": "💛", "rule": "Be as kind to yourself as you'd be to a friend."},
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


@router.post("/api/wellness")
async def save_wellness(body: dict) -> JSONResponse:
    """Save the lists (add/remove). Check-in state is preserved."""
    d = _data()
    d["nonneg"] = [{"id": (n.get("id") or "").strip() or f"n{i}",
                    "emoji": (n.get("emoji") or "•").strip(),
                    "label": (n.get("label") or "").strip(),
                    "note": (n.get("note") or "").strip()}
                   for i, n in enumerate(body.get("nonneg", [])) if (n.get("label") or "").strip()]
    d["routine"] = [{"time": (r.get("time") or "").strip(),
                     "emoji": (r.get("emoji") or "•").strip(),
                     "label": (r.get("label") or "").strip(),
                     "note": (r.get("note") or "").strip()}
                    for r in body.get("routine", []) if (r.get("label") or "").strip()]
    d["rules"] = [{"emoji": (r.get("emoji") or "•").strip(), "rule": (r.get("rule") or "").strip()}
                  for r in body.get("rules", []) if (r.get("rule") or "").strip()]
    store.save("wellness", d)
    return JSONResponse(d)


@router.get("/wellness", response_class=HTMLResponse)
async def wellness_page() -> HTMLResponse:
    return HTMLResponse(theme.page("Health & Wellness", _BODY, active="wellness"))


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
  /* inline editors — read as text until hovered/focused */
  .ed { background: transparent; border: 1px solid transparent; border-radius: 7px; color: inherit; font-family: inherit; font-size: inherit; padding: 3px 6px; box-sizing: border-box; width: 100%; }
  .ed:hover { border-color: var(--line-soft); }
  .ed:focus { outline: none; border-color: var(--gold-line); background: var(--field); }
  .ed.em { flex: 0 0 42px; text-align: center; }
  .nn { display: flex; align-items: flex-start; gap: 10px; padding: 6px 0; }
  .nn .box { width: 20px; height: 20px; border-radius: 6px; border: 2px solid var(--line); flex-shrink: 0; margin-top: 5px; display: flex; align-items: center; justify-content: center; font-size: 11px; cursor: pointer; }
  .nn.done .box { background: #80D4A0; border-color: #80D4A0; color: var(--bg); }
  .nn .nl { font-size: 14px; } .nn.done .nl { color: var(--muted); text-decoration: line-through; }
  .nn .nt { font-size: 11px; color: var(--muted); }
  .rt { display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: var(--panel); border: 1px solid var(--line-soft); border-left: 3px solid var(--gold); border-radius: 10px; margin-bottom: 8px; }
  .rt .rl { flex: 1; } .rt .rlab { font-size: 13px; } .rt .rnote { font-size: 10px; color: var(--muted); }
  .rt .rtime { flex: 0 0 88px; color: var(--gold); font-size: 11px; text-align: right; }
  .rule { display: flex; gap: 10px; align-items: center; background: var(--panel); border: 1px solid var(--line-soft); border-radius: 12px; padding: 11px 14px; margin-bottom: 9px; border-left: 3px solid var(--gold-line); }
  .rule .rr { font-size: 14px; line-height: 1.6; flex: 1; }
  .addrow { display: flex; gap: 8px; margin: 8px 0 4px; flex-wrap: wrap; }
  .addrow input { flex: 1; min-width: 80px; }
  .x { background: none; border: none; color: var(--muted); cursor: pointer; font-size: 13px; flex-shrink: 0; }
  .x:hover { color: #F08080; }
  .empty { color: var(--muted); font-style: italic; font-size: 13px; padding: 4px 0; }
</style>

<main>
  <div class="we-head"><h1>Health &amp; Wellness 🌿</h1></div>
  <div class="cat-tabs"><a href="/wellness" class="active">&#127807; Wellness</a><a href="/body">&#129728; Body</a></div>
  <p class="we-sub">your non-negotiables · your rules · your life — tap any line to edit</p>

  <div class="sec">Today's Check-in</div>
  <div class="checkin">
    <div class="ci-top"><span style="font-size:11px;letter-spacing:0.1em;color:var(--muted)">NON-NEGOTIABLES</span><span class="c" id="ci-count">0/0</span></div>
    <div class="ci-bar"><span id="ci-fill" style="width:0%"></span></div>
    <div id="nonneg"></div>
    <div class="addrow">
      <input id="nn-emoji" type="text" value="✅" style="flex:0 0 44px;min-width:0;text-align:center">
      <input id="nn-label" type="text" placeholder="A non-negotiable">
      <input id="nn-note" type="text" placeholder="Why it matters">
      <button class="btn btn-gold btn-sm" id="nn-add">Add</button>
    </div>
  </div>

  <div class="sec">Weekly Routine</div>
  <div id="routine"></div>
  <div class="addrow">
    <input id="rt-time" type="text" placeholder="Time" style="flex:0 0 80px;min-width:0">
    <input id="rt-emoji" type="text" value="⏰" style="flex:0 0 44px;min-width:0;text-align:center">
    <input id="rt-label" type="text" placeholder="What happens">
    <input id="rt-note" type="text" placeholder="Note (optional)">
    <button class="btn btn-gold btn-sm" id="rt-add">Add</button>
  </div>

  <div class="sec">Life Rules</div>
  <div id="rules"></div>
  <div class="addrow">
    <input id="ru-emoji" type="text" value="✦" style="flex:0 0 44px;min-width:0;text-align:center">
    <input id="ru-rule" type="text" placeholder="A rule to live by">
    <button class="btn btn-gold btn-sm" id="ru-add">Add</button>
  </div>
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

  // Non-negotiables: box toggles today's check-in; emoji/label/note edit inline.
  $("#nonneg").innerHTML = data.nonneg.length ? data.nonneg.map((n) => `<div class="nn ${isChecked(n.id) ? "done" : ""}">
    <div class="box" data-toggle="${esc(n.id)}">${isChecked(n.id) ? "✓" : ""}</div>
    <input class="ed em" data-f="emoji" data-id="${esc(n.id)}" value="${esc(n.emoji)}">
    <div style="flex:1">
      <input class="ed nl" data-f="label" data-id="${esc(n.id)}" value="${esc(n.label)}" placeholder="A non-negotiable">
      <input class="ed nt" data-f="note" data-id="${esc(n.id)}" value="${esc(n.note)}" placeholder="why it matters">
    </div>
    <button class="x" data-rm-nn="${esc(n.id)}">✕</button></div>`).join("") : '<div class="empty">None yet — add your non-negotiables below.</div>';
  $("#nonneg").querySelectorAll("[data-toggle]").forEach(el => el.addEventListener("click", () => toggle(el.dataset.toggle)));
  $("#nonneg").querySelectorAll("[data-f]").forEach(el => el.addEventListener("change", () => {
    const n = data.nonneg.find(x => x.id === el.dataset.id); if (!n) return; n[el.dataset.f] = el.value; persist(false);
  }));
  $("#nonneg").querySelectorAll("[data-rm-nn]").forEach(b => b.addEventListener("click", () => { data.nonneg = data.nonneg.filter(x => x.id !== b.dataset.rmNn); save(); }));

  // Routine: time / emoji / label / note all editable.
  $("#routine").innerHTML = data.routine.length ? data.routine.map((r, i) => `<div class="rt">
    <input class="ed em" data-f="emoji" data-idx="${i}" value="${esc(r.emoji)}">
    <div class="rl">
      <input class="ed rlab" data-f="label" data-idx="${i}" value="${esc(r.label)}" placeholder="What happens">
      <input class="ed rnote" data-f="note" data-idx="${i}" value="${esc(r.note)}" placeholder="note (optional)">
    </div>
    <input class="ed rtime" data-f="time" data-idx="${i}" value="${esc(r.time)}" placeholder="Time">
    <button class="x" data-rm-rt="${i}">✕</button></div>`).join("") : '<div class="empty">No routine yet — add steps below.</div>';
  $("#routine").querySelectorAll("[data-f]").forEach(el => el.addEventListener("change", () => {
    const r = data.routine[+el.dataset.idx]; if (!r) return; r[el.dataset.f] = el.value; persist(false);
  }));
  $("#routine").querySelectorAll("[data-rm-rt]").forEach(b => b.addEventListener("click", () => { data.routine.splice(+b.dataset.rmRt, 1); save(); }));

  // Rules: emoji + text editable.
  $("#rules").innerHTML = data.rules.length ? data.rules.map((r, i) => `<div class="rule">
    <input class="ed em" data-f="emoji" data-idx="${i}" value="${esc(r.emoji)}">
    <input class="ed rr" data-f="rule" data-idx="${i}" value="${esc(r.rule)}" placeholder="A rule to live by">
    <button class="x" data-rm-ru="${i}">✕</button></div>`).join("") : '<div class="empty">No rules yet — add some below.</div>';
  $("#rules").querySelectorAll("[data-f]").forEach(el => el.addEventListener("change", () => {
    const r = data.rules[+el.dataset.idx]; if (!r) return; r[el.dataset.f] = el.value; persist(false);
  }));
  $("#rules").querySelectorAll("[data-rm-ru]").forEach(b => b.addEventListener("click", () => { data.rules.splice(+b.dataset.rmRu, 1); save(); }));
}

async function toggle(id) {
  data = await (await fetch("/api/wellness/check", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ id }) })).json();
  render();
}
// reRender=false keeps focus steady after an inline text edit; true rebuilds the lists.
async function persist(reRender) {
  try { data = await (await fetch("/api/wellness", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(data) })).json(); } catch (_) {}
  if (reRender) render();
}
const save = () => persist(true);

function addNonneg() {
  const label = $("#nn-label").value.trim(); if (!label) return;
  data.nonneg.push({ id: "n" + Date.now(), emoji: $("#nn-emoji").value.trim() || "✅", label, note: $("#nn-note").value.trim() });
  $("#nn-label").value = ""; $("#nn-note").value = ""; $("#nn-emoji").value = "✅"; save();
}
function addRoutine() {
  const label = $("#rt-label").value.trim(); if (!label) return;
  data.routine.push({ time: $("#rt-time").value.trim(), emoji: $("#rt-emoji").value.trim() || "⏰", label, note: $("#rt-note").value.trim() });
  $("#rt-time").value = ""; $("#rt-label").value = ""; $("#rt-note").value = ""; $("#rt-emoji").value = "⏰"; save();
}
function addRule() {
  const rule = $("#ru-rule").value.trim(); if (!rule) return;
  data.rules.push({ emoji: $("#ru-emoji").value.trim() || "✦", rule });
  $("#ru-rule").value = ""; $("#ru-emoji").value = "✦"; save();
}
$("#nn-add").addEventListener("click", addNonneg);
$("#rt-add").addEventListener("click", addRoutine);
$("#ru-add").addEventListener("click", addRule);
// Enter in any add-row text field submits that row.
[["#nn-label", addNonneg], ["#nn-note", addNonneg], ["#rt-label", addRoutine], ["#rt-note", addRoutine], ["#ru-rule", addRule]]
  .forEach(([sel, fn]) => $(sel).addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); fn(); } }));

(async () => { try { data = await (await fetch("/api/wellness")).json(); } catch (_) {} render(); })();
</script>
"""
