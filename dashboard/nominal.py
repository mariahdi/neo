"""Nominal (NEO-39) — the budget module, ported from the Aria reference app.

Take-home income split into Fixed / Loose / Float / Savings categories, each
toggleable and editable, with a live "leftover" and a spend breakdown. Every
dollar figure goes through the audience view-modes engine (data-real = the true
amount, data-avg = the shareable average), so the page masks itself for
Friends / Coworker / Public. State persists to the store.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from . import store, theme

router = APIRouter()

# Seed budget (mock until edited). amount = private/true, avg = shareable.
DEFAULT = {
    "income": 10200,
    "income_avg": 7500,
    "categories": [
        {"id": 1, "name": "Rent", "emoji": "🏠", "amount": 3200, "avg": 2200, "type": "fixed", "active": True},
        {"id": 2, "name": "Car Insurance", "emoji": "🚗", "amount": 156, "avg": 150, "type": "fixed", "active": True},
        {"id": 3, "name": "Renters Insurance", "emoji": "🛡️", "amount": 12, "avg": 15, "type": "fixed", "active": True},
        {"id": 4, "name": "Utilities", "emoji": "💡", "amount": 250, "avg": 200, "type": "fixed", "active": True},
        {"id": 5, "name": "Food & Dining", "emoji": "🍽️", "amount": 800, "avg": 600, "type": "loose", "active": True},
        {"id": 6, "name": "Pocket Money", "emoji": "✨", "amount": 500, "avg": 400, "type": "loose", "active": True},
        {"id": 7, "name": "Health & Rx", "emoji": "💊", "amount": 100, "avg": 120, "type": "loose", "active": True},
        {"id": 8, "name": "Debt Payment", "emoji": "💳", "amount": 1500, "avg": 300, "type": "float", "active": True},
        {"id": 9, "name": "Emergency Fund", "emoji": "🚨", "amount": 200, "avg": 200, "type": "float", "active": True},
        {"id": 10, "name": "Vacay Fund", "emoji": "🌴", "amount": 600, "avg": 150, "type": "float", "active": True},
        {"id": 11, "name": "Roth IRA", "emoji": "🌱", "amount": 583, "avg": 500, "type": "savings", "active": True},
        {"id": 12, "name": "Next Spot", "emoji": "🏡", "amount": 250, "avg": 200, "type": "float", "active": True},
    ],
}


def _data() -> dict:
    return store.load("nominal", DEFAULT)


@router.get("/api/nominal")
async def get_nominal() -> JSONResponse:
    return JSONResponse(_data())


class NominalIn(BaseModel):
    income: float = 0
    income_avg: float = 0
    categories: list[dict] = []


@router.post("/api/nominal")
async def save_nominal(body: NominalIn) -> JSONResponse:
    clean = []
    for c in body.categories:
        name = (c.get("name") or "").strip()
        if not name:
            continue
        try:
            amount = max(0, round(float(c.get("amount", 0))))
        except (TypeError, ValueError):
            amount = 0
        try:
            avg = max(0, round(float(c.get("avg", amount))))
        except (TypeError, ValueError):
            avg = amount
        clean.append({
            "id": c.get("id"),
            "name": name,
            "emoji": (c.get("emoji") or "💫").strip(),
            "amount": amount,
            "avg": avg,
            "type": c.get("type") if c.get("type") in ("fixed", "loose", "float", "savings") else "loose",
            "active": bool(c.get("active", True)),
        })
    data = {
        "income": max(0, round(float(body.income or 0))),
        "income_avg": max(0, round(float(body.income_avg or 0))),
        "categories": clean,
    }
    store.save("nominal", data)
    return JSONResponse(data)


@router.get("/nominal", response_class=HTMLResponse)
async def nominal_page() -> HTMLResponse:
    return HTMLResponse(theme.page("Nominal", _BODY, active="nominal"))


_BODY = r"""
<style>
  :root { --cf-fixed: #F08080; --cf-loose: #F0D080; --cf-float: #80D4A0; --cf-savings: #80B8F0; }
  .nom-head h1 { font-size: 40px; } .nom-head h1 b { color: var(--gold); font-weight: 400; }
  .nom-sub { font-size: 12.5px; color: var(--muted); margin: 2px 0 22px; }
  .leftover { display: flex; align-items: center; justify-content: space-between; border-radius: 14px; padding: 22px; margin-bottom: 22px; border: 1px solid; }
  .leftover.good { background: linear-gradient(135deg, rgba(128,212,160,0.10), transparent); border-color: var(--cf-float); }
  .leftover.bad  { background: linear-gradient(135deg, rgba(240,128,128,0.10), transparent); border-color: var(--cf-fixed); }
  .leftover .lab { font-size: 10px; letter-spacing: 0.18em; text-transform: uppercase; }
  .leftover .big { font-size: 34px; font-weight: 700; }
  .leftover .spend { text-align: right; }
  .leftover .spend .lab { color: var(--muted); }
  .leftover .spend .v { font-size: 20px; }
  .glance { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 14px; padding: 18px 20px; margin-bottom: 22px; }
  .glance .gl-row { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end; min-height: 72px; }
  .glance .gi { display: flex; flex-direction: column; align-items: center; gap: 3px; }
  .glance .gi .pc { font-size: 9px; color: var(--muted); }
  .grp { margin-bottom: 22px; }
  .grp-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; }
  .grp-head .t { font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase; font-weight: 600; }
  .grp-head .sum { font-size: 12px; color: var(--muted); }
  .cat { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 12px; padding: 13px 16px; margin-bottom: 9px; border-left: 3px solid var(--line); }
  .cat.on { border-left-color: var(--cc); }
  .cat-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
  .cat-left { display: flex; align-items: center; gap: 11px; min-width: 0; }
  .toggle { width: 32px; height: 18px; border-radius: 9px; background: var(--faint, var(--field)); position: relative; cursor: pointer; flex-shrink: 0; transition: background 0.2s; }
  .toggle.on { background: var(--cc); }
  .toggle .knob { position: absolute; top: 3px; left: 3px; width: 12px; height: 12px; border-radius: 50%; background: var(--text); transition: left 0.2s; }
  .toggle.on .knob { left: 17px; }
  .cat .nm { font-size: 14px; } .cat .pct { font-size: 10px; color: var(--muted); }
  .cat .amt { font-size: 16px; font-weight: 700; color: var(--cc); cursor: pointer; white-space: nowrap; }
  .cat .adj { font-size: 9px; color: var(--muted); text-align: right; }
  .editor { margin-top: 12px; }
  .editor input[type=range] { width: 100%; }
  .editor .nums { display: flex; gap: 8px; margin-bottom: 8px; align-items: center; }
  .editor .nums input { flex: 1; text-align: center; font-weight: 700; }
  .rm { margin-top: 8px; font-size: 11px; color: var(--cf-fixed); cursor: pointer; text-align: center; padding: 6px; border: 1px solid color-mix(in srgb, var(--cf-fixed) 30%, transparent); border-radius: 8px; }
  .breakdown { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 14px; padding: 18px 20px; margin-bottom: 22px; }
  .bd-row { display: flex; align-items: center; gap: 10px; margin-bottom: 9px; }
  .bd-row .nm { width: 80px; font-size: 11px; text-transform: capitalize; color: var(--muted); }
  .bd-row .bar { flex: 1; height: 8px; border-radius: 5px; background: var(--field); overflow: hidden; }
  .bd-row .bar > span { display: block; height: 100%; border-radius: 5px; }
  .bd-row .v { width: 78px; text-align: right; font-size: 12px; }
  .add { display: flex; gap: 8px; margin-bottom: 22px; }
  .add input.n { flex: 1; } .add input.e { width: 52px; text-align: center; } .add input.a { width: 90px; }
</style>

<main>
  <div class="nom-head"><h1>Nominal <b>💰</b></h1></div>
  <p class="nom-sub">take-home · <span class="mask" data-type="currency" id="inc-sub">$0</span>/mo</p>

  <div id="leftover"></div>
  <div class="glance"><div class="gl-row" id="glance"></div>
    <div style="font-size:10px;color:var(--muted);margin-top:10px;">bigger emoji = more budget</div></div>

  <div id="groups"></div>

  <div class="add">
    <input class="e" id="add-emoji" type="text" value="💫">
    <input class="n" id="add-name" type="text" placeholder="New category">
    <input class="a" id="add-amount" type="number" placeholder="Amount">
    <select id="add-type">
      <option value="fixed">Fixed</option><option value="loose" selected>Loose</option>
      <option value="float">Float</option><option value="savings">Savings</option>
    </select>
    <button class="btn btn-gold btn-sm" id="add-btn">Add</button>
  </div>

  <div class="breakdown">
    <div class="section-label" style="margin-bottom:14px;">Spend breakdown</div>
    <div id="breakdown"></div>
  </div>
</main>

<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])));
const TYPES = ["fixed","loose","float","savings"];
const TLABEL = { fixed: "Fixed 🔒", loose: "Loose 〰️", float: "Float 🌊", savings: "Savings 🌱" };
const TCOLOR = { fixed: "#F08080", loose: "#F0D080", float: "#80D4A0", savings: "#80B8F0" };
let data = { income: 0, income_avg: 0, categories: [] };
let editing = null;

const fmt = (n) => "$" + Math.round(Number(n)||0).toLocaleString();
const incomeNow = () => data.income || 0;
const spend = () => data.categories.filter(c => c.active).reduce((a, c) => a + (Number(c.amount)||0), 0);
// A masked-currency span: real value + shareable average, engine fills the text.
const m = (real, avg) => `<span class="mask" data-type="currency" data-real="${esc(String(real))}"${avg!==undefined?` data-avg="${esc(String(avg))}"`:""}>${fmt(real)}</span>`;

function renderLeftover() {
  const left = incomeNow() - spend();
  const good = left >= 0;
  $("#leftover").innerHTML = `<div class="leftover ${good?"good":"bad"}">
    <div><div class="lab" style="color:${good?"var(--cf-float)":"var(--cf-fixed)"}">${good?"Leftover":"Over budget"}</div>
      <div class="big" style="color:${good?"var(--cf-float)":"var(--cf-fixed)"}">${m(Math.abs(left))}</div></div>
    <div class="spend"><div class="lab">Spending</div><div class="v">${m(spend())}</div></div>
  </div>`;
}

function renderGlance() {
  const inc = incomeNow() || 1;
  const items = data.categories.filter(c => c.active).map(c => {
    const pct = (Number(c.amount)||0) / inc;
    const size = Math.max(16, Math.min(64, pct * 360));
    return `<div class="gi"><div style="font-size:${size}px;line-height:1">${esc(c.emoji)}</div><div class="pc">${Math.round(pct*100)}%</div></div>`;
  }).join("");
  $("#glance").innerHTML = items || '<div style="color:var(--muted);font-size:12px">No active categories.</div>';
}

function catCard(c) {
  const inc = incomeNow() || 1;
  const pct = Math.round((Number(c.amount)||0) / inc * 100);
  const isEd = editing === c.id;
  return `<div class="cat ${c.active?"on":""}" style="--cc:${TCOLOR[c.type]}">
    <div class="cat-row">
      <div class="cat-left">
        <div class="toggle ${c.active?"on":""}" data-toggle="${c.id}"><div class="knob"></div></div>
        <span style="font-size:20px">${esc(c.emoji)}</span>
        <div><div class="nm">${esc(c.name)}</div><div class="pct">${pct}% of income</div></div>
      </div>
      <div data-edit="${c.id}" style="cursor:pointer;text-align:right">
        <div class="amt">${m(c.amount, c.avg)}</div>
        <div class="adj">${isEd?"▲ close":"▼ adjust"}</div>
      </div>
    </div>
    ${isEd ? `<div class="editor">
      <div class="nums"><input type="number" data-amt="${c.id}" value="${esc(String(c.amount))}"><span style="color:var(--muted);font-size:13px">/mo</span></div>
      <input type="range" min="0" max="5000" step="25" value="${esc(String(c.amount))}" data-range="${c.id}" style="accent-color:${TCOLOR[c.type]}">
      ${c.custom ? `<div class="rm" data-rm="${c.id}">🗑 remove this category</div>` : ""}
    </div>` : ""}
  </div>`;
}

function renderGroups() {
  $("#groups").innerHTML = TYPES.map(t => {
    const items = data.categories.filter(c => c.type === t);
    if (!items.length) return "";
    const total = items.filter(c => c.active).reduce((a, c) => a + (Number(c.amount)||0), 0);
    return `<div class="grp">
      <div class="grp-head"><span class="t" style="color:${TCOLOR[t]}">${TLABEL[t]}</span><span class="sum">${m(total)}</span></div>
      ${items.map(catCard).join("")}
    </div>`;
  }).join("");
  wireGroups();
}

function renderBreakdown() {
  const inc = incomeNow() || 1;
  const rows = TYPES.map(t => {
    const total = data.categories.filter(c => c.active && c.type === t).reduce((a, c) => a + (Number(c.amount)||0), 0);
    return { t, total, pct: total / inc };
  });
  const left = incomeNow() - spend();
  if (left > 0) rows.push({ t: "leftover", total: left, pct: left / inc, color: "var(--muted)" });
  $("#breakdown").innerHTML = rows.map(r => `<div class="bd-row">
    <div class="nm">${r.t}</div>
    <div class="bar"><span style="width:${Math.min(100, Math.round(r.pct*100))}%;background:${r.color || TCOLOR[r.t]}"></span></div>
    <div class="v">${m(r.total)}</div></div>`).join("");
}

function render() {
  $("#inc-sub").dataset.real = incomeNow();
  renderLeftover(); renderGlance(); renderGroups(); renderBreakdown();
  if (window.neoMaskScan) window.neoMaskScan();
}

async function save() {
  data = await (await fetch("/api/nominal", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(data) })).json();
  render();
}

function wireGroups() {
  document.querySelectorAll("[data-toggle]").forEach(el => el.addEventListener("click", () => {
    const c = data.categories.find(x => String(x.id) === el.dataset.toggle); if (c) { c.active = !c.active; save(); }
  }));
  document.querySelectorAll("[data-edit]").forEach(el => el.addEventListener("click", (e) => {
    if (e.target.closest(".editor")) return;
    const id = el.dataset.edit; editing = (String(editing) === id) ? null : (data.categories.find(x => String(x.id)===id)||{}).id; render();
  }));
  document.querySelectorAll("[data-range]").forEach(el => el.addEventListener("input", () => {
    const c = data.categories.find(x => String(x.id) === el.dataset.range); if (c) { c.amount = parseInt(el.value)||0;
      const ai = document.querySelector(`[data-amt="${el.dataset.range}"]`); if (ai) ai.value = c.amount; renderLeftover(); renderGlance(); renderBreakdown(); if(window.neoMaskScan) window.neoMaskScan(); }
  }));
  document.querySelectorAll("[data-range]").forEach(el => el.addEventListener("change", save));
  document.querySelectorAll("[data-amt]").forEach(el => el.addEventListener("change", () => {
    const c = data.categories.find(x => String(x.id) === el.dataset.amt); if (c) { c.amount = Math.max(0, parseInt(el.value)||0); save(); }
  }));
  document.querySelectorAll("[data-rm]").forEach(el => el.addEventListener("click", () => {
    data.categories = data.categories.filter(x => String(x.id) !== el.dataset.rm); editing = null; save();
  }));
}

$("#add-btn").addEventListener("click", () => {
  const name = $("#add-name").value.trim(); if (!name) return;
  const amount = Math.max(0, parseInt($("#add-amount").value) || 0);
  data.categories.push({ id: Date.now(), name, emoji: $("#add-emoji").value.trim() || "💫", amount, avg: amount, type: $("#add-type").value, active: true, custom: true });
  $("#add-name").value = ""; $("#add-amount").value = ""; $("#add-emoji").value = "💫";
  save();
});

// Re-mask when the audience view changes.
window.addEventListener("neo:view", () => { if (window.neoMaskScan) window.neoMaskScan(); });

(async () => { try { data = await (await fetch("/api/nominal")).json(); } catch (_) {} render(); })();
</script>
"""
