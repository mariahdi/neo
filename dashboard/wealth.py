"""Wealth (NEO-42) — investments + retirement projections, ported from Aria.

Investment accounts roll up to a total; from there it projects forward with a
monthly contribution and an assumed return, at a few horizons. Every dollar
runs through the audience masking engine (private real, otherwise rounded /
hidden / playful), so this stays as private as you want. State persists to the
store.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

from . import store, theme

router = APIRouter()

# Sample accounts + numbers for inspiration — shown until you make it your own.
DEFAULT = {"age": 30, "monthly": 500, "return": 8, "accounts": [
    {"id": "a-checking", "name": "Checking", "balance": 3200, "icon": "💳"},
    {"id": "a-savings", "name": "Savings", "balance": 8000, "icon": "🏦"},
    {"id": "a-401k", "name": "401(k)", "balance": 24000, "icon": "📈"},
]}


def _data() -> dict:
    return store.load("wealth", DEFAULT)


@router.get("/api/wealth")
async def get_wealth() -> JSONResponse:
    return JSONResponse(_data())


@router.post("/api/wealth")
async def save_wealth(body: dict) -> JSONResponse:
    # `return` is a Python keyword, so the payload is taken as a plain dict.
    accounts = []
    for a in body.get("accounts", []):
        name = (a.get("name") or "").strip()
        if not name:
            continue
        try:
            bal = max(0, round(float(a.get("balance", 0))))
        except (TypeError, ValueError):
            bal = 0
        accounts.append({"id": a.get("id"), "name": name,
                         "balance": bal, "icon": (a.get("icon") or "💰").strip()})
    data = {
        "age": int(body.get("age", 28) or 28),
        "monthly": max(0, round(float(body.get("monthly", 0) or 0))),
        "return": float(body.get("return", 8) or 8),
        "accounts": accounts,
    }
    store.save("wealth", data)
    return JSONResponse(data)


@router.get("/wealth", response_class=HTMLResponse)
async def wealth_page() -> HTMLResponse:
    return HTMLResponse(theme.page("Finance & Wealth", _BODY, active="wealth"))


_BODY = r"""
<style>
  .w-head h1 { font-size: 40px; } .w-head h1 b { color: var(--gold); font-weight: 400; }
  .w-sub { font-size: 12.5px; color: var(--muted); margin: 2px 0 22px; }
  .total { background: linear-gradient(135deg, rgba(128,212,160,0.10), transparent); border: 1px solid color-mix(in srgb, #80D4A0 40%, transparent); border-radius: 16px; padding: 24px; margin-bottom: 18px; }
  .total .lab { font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase; color: #80D4A0; }
  .total .big { font-size: 42px; font-weight: 700; color: #80D4A0; margin-top: 6px; }
  .total .meta { font-size: 12px; color: var(--muted); margin-top: 6px; }
  .accts { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 18px; }
  .acct { background: var(--field); border-radius: 10px; padding: 12px 14px; border-left: 2px solid #80D4A0; }
  .acct .an { font-size: 11px; color: var(--muted); } .acct .ab { font-size: 17px; font-weight: 700; color: #80D4A0; margin-top: 2px; }
  .controls { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 22px; }
  .controls .ctl { flex: 1; min-width: 120px; } .controls label { font-size: 10px; color: var(--muted); letter-spacing: 0.1em; text-transform: uppercase; display: block; margin-bottom: 5px; }
  .controls input { width: 100%; }
  .proj { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 14px; padding: 18px 20px; margin-bottom: 18px; }
  .proj .r { display: flex; justify-content: space-between; align-items: center; padding: 11px 0; border-bottom: 1px solid var(--line-soft); }
  .proj .r:last-child { border-bottom: none; }
  .proj .r.hi { color: var(--gold); }
  .proj .lab { font-size: 14px; } .proj .lab .age { font-size: 11px; color: var(--muted); }
  .proj .v { text-align: right; } .proj .v .tot { font-size: 18px; font-weight: 700; } .proj .v .roi { font-size: 11px; color: #80D4A0; }
  .manage { display: flex; gap: 8px; margin-bottom: 18px; }
  .manage input.n { flex: 1; } .manage input.b { width: 110px; } .manage input.i { width: 48px; text-align: center; }
  .mrow { display: flex; gap: 8px; margin-bottom: 8px; align-items: center; }
  .mrow input.n { flex: 1; } .mrow input.b { width: 120px; } .mrow input.i { width: 48px; text-align: center; }
</style>

<main>
  <div class="w-head"><h1>Finance &amp; Wealth 📊</h1></div>
  <div class="cat-tabs"><a href="/nominal">&#128176; Budget</a><a href="/wealth" class="active">&#128202; Investments</a><a href="/stocks">&#128200; Stocks</a></div>
  <p class="w-sub">long game · the trajectory is up</p>

  <div class="total">
    <div class="lab">Total invested assets</div>
    <div class="big"><span class="mask" data-type="currency" id="total">$0</span></div>
    <div class="meta"><span id="acct-count">0</span> accounts · age <span id="age-label">28</span></div>
    <div class="accts" id="accts"></div>
  </div>

  <div class="controls">
    <div class="ctl"><label>Monthly add</label><input type="number" id="monthly"></div>
    <div class="ctl"><label>Return %</label><input type="number" id="return"></div>
    <div class="ctl"><label>Age now</label><input type="number" id="age"></div>
  </div>

  <div class="section-label" style="margin-bottom:10px;">Retirement projections</div>
  <div class="proj" id="proj"></div>

  <div class="section-label" style="margin-bottom:10px;">Accounts</div>
  <div id="mrows"></div>
  <div class="manage">
    <input class="i" id="add-icon" type="text" value="💰">
    <input class="n" id="add-name" type="text" placeholder="Account name">
    <input class="b" id="add-bal" type="number" placeholder="Balance">
    <button class="btn btn-gold btn-sm" id="add-btn">Add</button>
  </div>
</main>

<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])));
let data = { age: 28, monthly: 0, return: 8, accounts: [] };

const fmt = (n) => "$" + Math.round(Number(n)||0).toLocaleString();
const fmtShort = (n) => { n = Number(n)||0; return n >= 1e6 ? "$"+(n/1e6).toFixed(2)+"M" : n >= 1e3 ? "$"+Math.round(n/1e3)+"k" : "$"+Math.round(n); };
const total = () => data.accounts.reduce((a, c) => a + (Number(c.balance)||0), 0);
const m = (real) => `<span class="mask" data-type="currency" data-real="${esc(String(Math.round(real)))}">${fmt(real)}</span>`;

function project(years) {
  const r = (Number(data.return)||8) / 100;
  const P = total();
  const c = (Number(data.monthly)||0) * 12;
  const fv = P * Math.pow(1+r, years) + (r ? c * ((Math.pow(1+r, years) - 1) / r) : c * years);
  const contributed = P + c * years;
  const roi = contributed ? ((fv - contributed) / contributed * 100) : 0;
  return { fv, contributed, roi };
}

function renderTotal() {
  $("#total").dataset.real = Math.round(total());
  $("#acct-count").textContent = data.accounts.length;
  $("#age-label").textContent = data.age;
  $("#accts").innerHTML = data.accounts.map(a => `<div class="acct">
    <div class="an">${esc(a.icon)} ${esc(a.name)}</div><div class="ab">${m(a.balance)}</div></div>`).join("");
}

function renderProj() {
  const horizons = [1, 5, 10, 20, 30, 40];
  $("#proj").innerHTML = horizons.map(y => {
    const p = project(y);
    const hi = y === 40;
    return `<div class="r ${hi?"hi":""}">
      <div class="lab">${y} Year${y>1?"s":""} <span class="age">(age ${(Number(data.age)||28)+y})</span></div>
      <div class="v"><div class="tot" style="${hi?"color:var(--gold)":"color:#80D4A0"}">${m(p.fv)}</div>
        <div class="roi">+${p.roi.toFixed(0)}%</div></div>
    </div>`;
  }).join("");
}

function renderManage() {
  $("#mrows").innerHTML = data.accounts.map(a => `<div class="mrow" data-id="${esc(String(a.id))}">
    <input class="i" type="text" value="${esc(a.icon)}">
    <input class="n" type="text" value="${esc(a.name)}">
    <input class="b" type="number" value="${esc(String(a.balance))}">
    <button class="btn btn-sm rm" type="button">✕</button></div>`).join("");
  $("#mrows").querySelectorAll(".mrow").forEach(row => {
    const id = row.dataset.id;
    row.querySelector(".rm").addEventListener("click", () => { data.accounts = data.accounts.filter(a => String(a.id) !== id); save(); });
    row.querySelectorAll("input").forEach(inp => inp.addEventListener("change", () => {
      const a = data.accounts.find(x => String(x.id) === id);
      if (a) { a.icon = row.querySelector(".i").value.trim() || "💰"; a.name = row.querySelector(".n").value.trim(); a.balance = Math.max(0, parseInt(row.querySelector(".b").value)||0); save(); }
    }));
  });
}

function render() { renderTotal(); renderProj(); renderManage();
  $("#monthly").value = data.monthly; $("#return").value = data.return; $("#age").value = data.age;
  if (window.neoMaskScan) window.neoMaskScan(); }

async function save() {
  data = await (await fetch("/api/wealth", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(data) })).json();
  render();
}

["monthly","return","age"].forEach(k => $("#"+k).addEventListener("change", () => {
  data[k] = parseFloat($("#"+k).value) || 0; save();
}));
$("#add-btn").addEventListener("click", () => {
  const name = $("#add-name").value.trim(); if (!name) return;
  data.accounts.push({ id: Date.now(), name, balance: Math.max(0, parseInt($("#add-bal").value)||0), icon: $("#add-icon").value.trim() || "💰" });
  $("#add-name").value = ""; $("#add-bal").value = ""; $("#add-icon").value = "💰"; save();
});
window.addEventListener("neo:view", () => { if (window.neoMaskScan) window.neoMaskScan(); });

(async () => { try { data = await (await fetch("/api/wealth")).json(); } catch (_) {} render(); })();
</script>
"""
