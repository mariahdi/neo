"""Stocks (NEO-30) — sector-organized watchlist with daily AI briefings.

Sectors hold stocks; each stock can carry a short "daily update" briefing.
You can add / swap / remove sectors and stocks. Structure persists to the JSON
store (dashboard/data/stocks.json).

The briefings: the *real* plan is a scheduled (cron) job that, once a day,
calls the Anthropic API per stock and writes the update into the store — see
STUB / TODO at refresh_update(). Until that job exists, the page exposes a
"Refresh (AI preview)" button that runs the same Anthropic call **live,
on-demand**, so the output is real Claude text; the cron just automates it.

IMPORTANT caveat (surfaced in the UI): Claude has no live market feed, so a
briefing reflects its training knowledge, not today's price. A production
daily update would pair this with a real market-data source.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import requests
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from . import store, theme

router = APIRouter()

ANTHROPIC_KEY = os.environ.get("NEO_ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.environ.get("NEO_ANTHROPIC_MODEL", "claude-sonnet-4-6")

# Live market data via Finnhub (finnhub.io) — free real-time US quotes.
STOCK_API_KEY = os.environ.get("NEO_STOCK_API_KEY")


def _quote(ticker: str) -> dict | None:
    """Live quote for a US ticker. Returns {price, change, pct} or None
    (no key, network error, or a symbol with no price — e.g. a private company)."""
    ticker = (ticker or "").strip().upper()
    if not (ticker and STOCK_API_KEY):
        return None
    try:
        r = requests.get("https://finnhub.io/api/v1/quote",
                         params={"symbol": ticker, "token": STOCK_API_KEY}, timeout=15)
        r.raise_for_status()
        d = r.json()
        if not d.get("c"):  # current price 0/None -> unknown symbol
            return None
        return {"price": round(d["c"], 2), "change": round(d.get("d") or 0, 2),
                "pct": round(d.get("dp") or 0, 2)}
    except Exception as e:
        print(f"[stocks] quote {ticker} failed: {e}")
        return None

# Seed watchlist (mock until edited).
DEFAULT = {"sectors": []}


def _data() -> dict:
    return store.load("stocks", DEFAULT)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ── Daily briefing ────────────────────────────────────────────────────────────
def _mock_update(name: str, ticker: str) -> str:
    tag = f" ({ticker})" if ticker else ""
    return (
        f"[Sample briefing] {name}{tag} held roughly steady today on average "
        "volume, with no major company-specific news. Sentiment tracks the "
        "broader sector. — placeholder until the Anthropic key is set."
    )


def _claude_update(name: str, ticker: str) -> str:
    """Live Anthropic call for one stock's briefing. Real Claude text, but not
    real-time market data (see module docstring)."""
    tag = f" (ticker {ticker})" if ticker else " (privately held)"
    prompt = (
        f"Give a concise daily briefing on {name}{tag} for a personal "
        "watchlist dashboard. 3-4 sentences: recent direction/performance, any "
        "notable news or catalysts, and a brief outlook. If it's a private "
        "company, give a business update instead of a stock price. Be factual "
        "and plain-spoken. Do not invent a specific real-time price — you don't "
        "have live market data; speak to trend and context."
    )
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": 400,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=40,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"].strip()


# === SCHEDULED-JOB STUB =======================================================
# TODO (real integration): a daily cron (Render Cron Job / GitHub Action /
# scheduled task) should iterate every stock and call _claude_update(), writing
# the result + timestamp into the store — exactly what refresh_update() does
# for one stock below, looped over all of them on a schedule. Pair it with a
# market-data API for real prices. The button is the same call, run on demand.
# ==============================================================================


# ── API ───────────────────────────────────────────────────────────────────────
@router.get("/api/stocks")
async def get_stocks() -> JSONResponse:
    return JSONResponse(_data())


@router.get("/api/stocks/quotes")
async def get_quotes(symbols: str = "") -> JSONResponse:
    """Live quotes for the given comma-separated tickers."""
    out = {}
    for t in {s.strip().upper() for s in symbols.split(",") if s.strip()}:
        q = _quote(t)
        if q:
            out[t] = q
    return JSONResponse({"quotes": out, "live": bool(STOCK_API_KEY)})


class StocksIn(BaseModel):
    sectors: list[dict] = []


@router.post("/api/stocks")
async def save_stocks(body: StocksIn) -> JSONResponse:
    """Replace the sector/stock structure (add/swap/remove). Existing briefings
    ride along in what the client sends back, so they're preserved."""
    clean = []
    for s in body.sectors:
        name = (s.get("name") or "").strip()
        if not name:
            continue
        stocks = []
        for st in s.get("stocks", []):
            sname = (st.get("name") or "").strip()
            if not sname:
                continue
            stocks.append({
                "name": sname,
                "ticker": (st.get("ticker") or "").strip().upper(),
                "update": st.get("update"),
                "updated_at": st.get("updated_at"),
            })
        clean.append({"id": (s.get("id") or name.lower().replace(" ", "-")), "name": name, "stocks": stocks})
    data = {"sectors": clean}
    store.save("stocks", data)
    return JSONResponse(data)


class RefreshIn(BaseModel):
    sector_id: str
    name: str
    ticker: str = ""


@router.post("/api/stocks/refresh")
async def refresh_update(body: RefreshIn) -> JSONResponse:
    """Generate one stock's briefing now (live Anthropic call, or a mock when
    no key is set) and persist it. This is the on-demand twin of the daily job."""
    demo = not ANTHROPIC_KEY
    try:
        text = _mock_update(body.name, body.ticker) if demo else _claude_update(body.name, body.ticker)
    except Exception as e:
        print(f"[stocks] briefing for {body.name} failed: {e}")
        return JSONResponse({"ok": False, "message": "Couldn't generate a briefing — try again."}, status_code=502)

    stamp = _now()
    data = _data()
    for sec in data["sectors"]:
        if sec.get("id") != body.sector_id:
            continue
        for st in sec["stocks"]:
            if st["name"] == body.name and (st.get("ticker") or "") == body.ticker:
                st["update"] = text
                st["updated_at"] = stamp
    store.save("stocks", data)
    return JSONResponse({"ok": True, "update": text, "updated_at": stamp, "demo": demo})


# ── Page ──────────────────────────────────────────────────────────────────────
@router.get("/stocks", response_class=HTMLResponse)
async def stocks_page() -> HTMLResponse:
    return HTMLResponse(theme.page("Stocks", _BODY, active="stocks"))


_BODY = r"""
<style>
  .stk-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 6px; }
  .stk-head h1 { font-size: 40px; }
  .stk-head h1 b { color: var(--gold); font-weight: 400; }
  .note { font-size: 12px; color: var(--muted); margin: 2px 0 24px; max-width: 640px; line-height: 1.5; }
  .note b { color: var(--gold); font-weight: 600; }
  .sector { margin-bottom: 26px; }
  .sector-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
  .sector-head h2 { font-size: 22px; letter-spacing: 0.05em; }
  .sector-head .count { font-size: 11px; font-weight: 700; color: #1a1305; background: var(--gold); border-radius: 20px; padding: 1px 9px; }
  .stocks-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; }
  .stock { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 12px; padding: 16px; }
  .stock-top { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
  .stock-name { font-size: 15px; font-weight: 700; }
  .stock-ticker { font-size: 11px; color: var(--gold); font-weight: 700; letter-spacing: 0.06em; }
  .stock-price { margin: 9px 0 2px; min-height: 18px; }
  .stock-price .px { font-size: 19px; font-weight: 700; }
  .stock-price .chg { font-size: 12px; margin-left: 7px; font-weight: 600; }
  .stock-price .chg.up { color: #80D4A0; } .stock-price .chg.down { color: #F08080; }
  .stock-price .px-none { font-size: 10.5px; color: var(--muted); }
  .stock-update { font-size: 13px; line-height: 1.65; color: #cdd5e8; margin: 12px 0; white-space: pre-wrap; }
  .stock-update.empty { color: #56638a; font-style: italic; }
  .stock-foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .stamp { font-size: 11px; color: var(--muted); }
  .sector-empty { color: #56638a; font-style: italic; font-size: 13px; padding: 6px 2px; }
  .preview-tag { font-size: 9px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--gold); border: 1px solid var(--gold-line); border-radius: 20px; padding: 1px 7px; }
  /* manage mode */
  .mrow { display: flex; gap: 8px; margin-bottom: 8px; align-items: center; }
  .mrow input.n { flex: 1; } .mrow input.t { width: 90px; text-transform: uppercase; }
  .msector { border: 1px dashed var(--line); border-radius: 12px; padding: 14px; margin-bottom: 14px; }
  .msector .shead { display: flex; gap: 8px; align-items: center; margin-bottom: 10px; }
  .msector .shead input { flex: 1; font-weight: 700; }
  .spin { display: inline-block; width: 12px; height: 12px; border: 2px solid var(--gold); border-right-color: transparent; border-radius: 50%; animation: sp 0.7s linear infinite; vertical-align: -1px; }
  @keyframes sp { to { transform: rotate(360deg); } }
  .actions { display: flex; gap: 10px; margin-top: 8px; }
</style>

<main>
  <div class="stk-head">
    <h1>Stocks <b>Watch</b></h1>
    <button class="btn btn-sm" id="manage-btn">Manage</button>
  </div>
  <p class="note" id="note"></p>

  <div id="view"></div>

  <div id="manage" style="display:none;">
    <div id="msectors"></div>
    <button class="btn btn-sm" id="add-sector">+ Add sector</button>
    <div class="actions">
      <button class="btn btn-gold btn-sm" id="save-manage">Save changes</button>
      <button class="btn btn-sm" id="cancel-manage">Cancel</button>
    </div>
  </div>
</main>

<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])));
let data = { sectors: [] };
let demoMode = false;

function fmtWhen(iso) {
  if (!iso) return "";
  const d = iso.slice(0,10), m=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const p=d.split("-"); const mo=m[parseInt(p[1],10)-1];
  return mo ? `${mo} ${parseInt(p[2],10)}` : d;
}

function renderNote() {
  const msg = {
    live: `Prices are <b>live</b> (real-time US quotes)${pricesAt ? ` · as of ${pricesAt}, auto-refreshing every minute` : ""}. Hit Refresh on a card for an AI briefing on top.`,
    loggedout: 'Briefings are a live <b>AI preview</b> (Claude text). <b>Log in</b> to see live <b>prices</b> on each card.',
    nokey: 'Briefings are a live <b>AI preview</b> (Claude text). For live <b>prices</b> on each card, add a free <code>NEO_STOCK_API_KEY</code> (finnhub.io).',
  };
  $("#note").innerHTML = msg[priceState] || msg.nokey;
}

function stockCard(sec, st) {
  const upd = (st.update || "").trim();
  const body = upd
    ? `<div class="stock-update">${esc(upd)}</div>`
    : '<div class="stock-update empty">No briefing yet — hit Refresh for an AI preview.</div>';
  const stamp = st.updated_at ? `<span class="stamp">Updated ${esc(fmtWhen(st.updated_at))}</span>` : '<span></span>';
  const tkr = (st.ticker || "").trim().toUpperCase();
  const px = tkr ? `<div class="stock-price" data-px="${esc(tkr)}"></div>` : "";
  return `<div class="stock">
    <div class="stock-top">
      <span class="stock-name">${esc(st.name)}</span>
      <span class="stock-ticker">${esc(st.ticker || "")}</span>
    </div>
    ${px}
    ${body}
    <div class="stock-foot">
      ${stamp}
      <button class="btn btn-sm refresh" data-sec="${esc(sec.id)}" data-name="${esc(st.name)}" data-ticker="${esc(st.ticker||"")}">↻ Refresh</button>
    </div>
  </div>`;
}

function render() {
  renderNote();
  const v = $("#view");
  v.innerHTML = data.sectors.map(sec => `
    <div class="sector">
      <div class="sector-head"><h2>${esc(sec.name)}</h2><span class="count">${sec.stocks.length}</span><span class="preview-tag">AI preview</span></div>
      ${sec.stocks.length
        ? `<div class="stocks-grid">${sec.stocks.map(st => stockCard(sec, st)).join("")}</div>`
        : '<div class="sector-empty">No stocks in this sector yet — use Manage to add one.</div>'}
    </div>`).join("");
  v.querySelectorAll(".refresh").forEach(b => b.addEventListener("click", onRefresh));
  loadQuotes();
}

let priceState = "nokey", pricesAt = "";
async function loadQuotes() {
  const tickers = [...new Set(data.sectors.flatMap(s => s.stocks.map(st => (st.ticker || "").trim().toUpperCase())).filter(Boolean))];
  if (!tickers.length) return;
  let res;
  try { res = await (await fetch("/api/stocks/quotes?symbols=" + encodeURIComponent(tickers.join(",")))).json(); }
  catch (_) { return; }
  // Live prices need an authenticated session; logged-out gets a clear prompt
  // instead of the misleading "add a key" hint.
  if (res && res.error === "unauthorized") {
    priceState = "loggedout";
    document.querySelectorAll("[data-px]").forEach(el => {
      el.innerHTML = '<span class="px-none">log in to see live prices</span>';
    });
    renderNote();
    return;
  }
  priceState = res.live ? "live" : "nokey";
  const quotes = res.quotes || {};
  document.querySelectorAll("[data-px]").forEach(el => {
    const q = quotes[el.dataset.px];
    if (q) {
      const up = q.change >= 0;
      el.innerHTML = `<span class="px">$${q.price.toLocaleString()}</span> <span class="chg ${up ? "up" : "down"}">${up ? "▲ +" : "▼ "}${q.pct}%</span>`;
    } else {
      el.innerHTML = priceState === "live" ? '<span class="px-none">— no live price</span>' : '<span class="px-none">add a market-data key for live prices</span>';
    }
  });
  if (priceState === "live" && Object.keys(quotes).length) pricesAt = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  renderNote();
}

async function load() {
  try { data = await (await fetch("/api/stocks")).json(); } catch (_) {}
  render();
}

async function onRefresh(e) {
  const b = e.currentTarget;
  b.disabled = true; b.innerHTML = '<span class="spin"></span> Briefing…';
  try {
    const r = await fetch("/api/stocks/refresh", {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ sector_id: b.dataset.sec, name: b.dataset.name, ticker: b.dataset.ticker }),
    });
    const out = await r.json();
    if (out.ok) {
      demoMode = out.demo;
      const sec = data.sectors.find(s => s.id === b.dataset.sec);
      const st = sec && sec.stocks.find(x => x.name === b.dataset.name && (x.ticker||"") === b.dataset.ticker);
      if (st) { st.update = out.update; st.updated_at = out.updated_at; }
      render();
    } else { alert(out.message || "Failed."); b.disabled = false; b.textContent = "↻ Refresh"; }
  } catch (_) { b.disabled = false; b.textContent = "↻ Refresh"; }
}

// ── Manage mode (add/swap/remove sectors + stocks) ──
function stockRow(st = {name:"", ticker:""}) {
  const row = document.createElement("div");
  row.className = "mrow";
  row.innerHTML = `<input class="n" type="text" placeholder="Company name — e.g. Archer Aviation" value="${esc(st.name)}">
                   <input class="t" type="text" placeholder="Ticker — e.g. ACHR" title="The stock symbol — this is what powers live prices" value="${esc(st.ticker||"")}">
                   <button class="btn btn-sm" type="button" title="Remove">✕</button>`;
  row.dataset.update = st.update || "";
  row.dataset.updatedAt = st.updated_at || "";
  row.querySelector("button").addEventListener("click", () => row.remove());
  return row;
}
function sectorBlock(sec = {id:"", name:"", stocks:[]}) {
  const block = document.createElement("div");
  block.className = "msector";
  block.dataset.id = sec.id || "";
  block.innerHTML = `<div class="shead">
      <input type="text" placeholder="Sector name" value="${esc(sec.name)}">
      <button class="btn btn-sm rm-sector" type="button">Remove sector</button>
    </div>
    <div class="rows"></div>
    <button class="btn btn-sm add-stock" type="button">+ Add stock</button>`;
  const rows = block.querySelector(".rows");
  sec.stocks.forEach(st => rows.appendChild(stockRow(st)));
  block.querySelector(".add-stock").addEventListener("click", () => rows.appendChild(stockRow()));
  block.querySelector(".rm-sector").addEventListener("click", () => block.remove());
  return block;
}
$("#manage-btn").addEventListener("click", () => {
  const c = $("#msectors"); c.innerHTML = "";
  data.sectors.forEach(s => c.appendChild(sectorBlock(s)));
  $("#view").style.display = "none"; $("#manage").style.display = "block"; $("#manage-btn").style.display = "none";
});
function closeManage() {
  $("#view").style.display = "block"; $("#manage").style.display = "none"; $("#manage-btn").style.display = "inline-block";
}
$("#cancel-manage").addEventListener("click", closeManage);
$("#add-sector").addEventListener("click", () => $("#msectors").appendChild(sectorBlock()));
$("#save-manage").addEventListener("click", async () => {
  const sectors = [...document.querySelectorAll("#msectors .msector")].map(block => {
    const name = block.querySelector(".shead input").value.trim();
    const stocks = [...block.querySelectorAll(".rows .mrow")].map(row => ({
      name: row.querySelector(".n").value.trim(),
      ticker: row.querySelector(".t").value.trim(),
      update: row.dataset.update || null,
      updated_at: row.dataset.updatedAt || null,
    })).filter(s => s.name);
    return { id: block.dataset.id, name, stocks };
  }).filter(s => s.name);
  data = await (await fetch("/api/stocks", {
    method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ sectors }),
  })).json();
  render(); closeManage();
});

load();
setInterval(loadQuotes, 60000);  // keep live prices fresh while the page is open
</script>
"""
