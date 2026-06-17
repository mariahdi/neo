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
    "nonneg": [],
    "routine": [],
    "rules": [],
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
  .rule .rr { font-size: 14px; line-height: 1.6; flex: 1; }
  .addrow { display: flex; gap: 8px; margin: 8px 0 4px; flex-wrap: wrap; }
  .addrow input { flex: 1; min-width: 80px; }
  .x { background: none; border: none; color: var(--muted); cursor: pointer; font-size: 13px; flex-shrink: 0; }
  .x:hover { color: #F08080; }
  .empty { color: var(--muted); font-style: italic; font-size: 13px; padding: 4px 0; }
</style>

<main>
  <div class="we-head"><h1>Wellness <b>🌸</b></h1></div>
  <p class="we-sub">your non-negotiables · your rules · your life</p>

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
  $("#nonneg").innerHTML = data.nonneg.length ? data.nonneg.map((n, i) => `<div class="nn ${isChecked(n.id) ? "done" : ""}" data-id="${esc(n.id)}">
    <div class="box">${isChecked(n.id) ? "✓" : ""}</div>
    <div style="flex:1"><div class="nl">${esc(n.emoji)} ${esc(n.label)}</div><div class="nt">${esc(n.note)}</div></div>
    <button class="x" data-rm-nn="${i}">✕</button></div>`).join("") : '<div class="empty">None yet — add your non-negotiables below.</div>';
  $("#nonneg").querySelectorAll("[data-id]").forEach(el => el.addEventListener("click", (e) => { if (e.target.closest("[data-rm-nn]")) return; toggle(el.dataset.id); }));
  $("#nonneg").querySelectorAll("[data-rm-nn]").forEach(b => b.addEventListener("click", (e) => { e.stopPropagation(); data.nonneg.splice(+b.dataset.rmNn, 1); save(); }));

  $("#routine").innerHTML = data.routine.length ? data.routine.map((r, i) => `<div class="rt">
    <span style="font-size:18px">${esc(r.emoji)}</span>
    <div class="rl"><div class="rlab">${esc(r.label)}</div><div class="rnote">${esc(r.note)}</div></div>
    <span class="rtime">${esc(r.time)}</span><button class="x" data-rm-rt="${i}">✕</button></div>`).join("") : '<div class="empty">No routine yet — add steps below.</div>';
  $("#routine").querySelectorAll("[data-rm-rt]").forEach(b => b.addEventListener("click", () => { data.routine.splice(+b.dataset.rmRt, 1); save(); }));

  $("#rules").innerHTML = data.rules.length ? data.rules.map((r, i) => `<div class="rule"><span style="font-size:20px">${esc(r.emoji)}</span><div class="rr">${esc(r.rule)}</div><button class="x" data-rm-ru="${i}">✕</button></div>`).join("") : '<div class="empty">No rules yet — add some below.</div>';
  $("#rules").querySelectorAll("[data-rm-ru]").forEach(b => b.addEventListener("click", () => { data.rules.splice(+b.dataset.rmRu, 1); save(); }));
}

async function toggle(id) {
  data = await (await fetch("/api/wellness/check", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ id }) })).json();
  render();
}
async function save() {
  data = await (await fetch("/api/wellness", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(data) })).json();
  render();
}

$("#nn-add").addEventListener("click", () => {
  const label = $("#nn-label").value.trim(); if (!label) return;
  data.nonneg.push({ id: "n" + Date.now(), emoji: $("#nn-emoji").value.trim() || "✅", label, note: $("#nn-note").value.trim() });
  $("#nn-label").value = ""; $("#nn-note").value = ""; $("#nn-emoji").value = "✅"; save();
});
$("#rt-add").addEventListener("click", () => {
  const label = $("#rt-label").value.trim(); if (!label) return;
  data.routine.push({ time: $("#rt-time").value.trim(), emoji: $("#rt-emoji").value.trim() || "⏰", label, note: "" });
  $("#rt-time").value = ""; $("#rt-label").value = ""; $("#rt-emoji").value = "⏰"; save();
});
$("#ru-add").addEventListener("click", () => {
  const rule = $("#ru-rule").value.trim(); if (!rule) return;
  data.rules.push({ emoji: $("#ru-emoji").value.trim() || "✦", rule });
  $("#ru-rule").value = ""; $("#ru-emoji").value = "✦"; save();
});

(async () => { try { data = await (await fetch("/api/wellness")).json(); } catch (_) {} render(); })();
</script>
"""
