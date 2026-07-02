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
from fastapi import APIRouter, Request
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

# Price history for the on-card sparkline. Finnhub's free tier doesn't include
# candles, so we pull free daily history (no key) from Yahoo Finance's chart
# endpoint and cache it for the day — the client only asks for a stock's history
# when its card is expanded, so this is never called for the compact view.
_history_cache: dict[str, tuple[str, list[float]]] = {}


def _history(ticker: str) -> list[float]:
    """Last ~30 daily closes for a US ticker, or [] if unavailable. Cached per day."""
    ticker = (ticker or "").strip().upper()
    if not ticker:
        return []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cached = _history_cache.get(ticker)
    if cached and cached[0] == today:
        return cached[1]
    closes: list[float] = []
    try:
        r = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
            params={"range": "1mo", "interval": "1d"},
            headers={"User-Agent": "Mozilla/5.0"},  # Yahoo blocks bare clients
            timeout=15,
        )
        r.raise_for_status()
        result = (r.json().get("chart") or {}).get("result") or []
        if result:
            raw = result[0]["indicators"]["quote"][0].get("close") or []
            closes = [round(float(x), 2) for x in raw if x is not None and float(x) > 0][-30:]
    except Exception as e:
        print(f"[stocks] history {ticker} failed: {e}")
        closes = []
    _history_cache[ticker] = (today, closes)
    return closes


# Sample watchlist of well-known names — shown until you make it your own
# (the moment you add/remove a stock, your version is saved instead).
DEFAULT = {"sectors": [
    {"id": "tech", "name": "Tech", "stocks": [
        {"name": "Apple", "ticker": "AAPL", "update": None, "updated_at": None},
        {"name": "Microsoft", "ticker": "MSFT", "update": None, "updated_at": None},
        {"name": "NVIDIA", "ticker": "NVDA", "update": None, "updated_at": None},
    ]},
    {"id": "space", "name": "Space", "stocks": [
        {"name": "SpaceX", "ticker": "SPCX", "update": None, "updated_at": None},
        {"name": "Rocket Lab", "ticker": "RKLB", "update": None, "updated_at": None},
    ]},
]}


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


def briefing_prompt(name: str, ticker: str) -> str:
    """The briefing prompt for one stock. Shared by the live call and the daily
    Batch job (dashboard/jobs/refresh_stocks.py) so both ask for the same thing."""
    tag = f" (ticker {ticker})" if ticker else " (privately held)"
    return (
        f"Give a concise daily briefing on {name}{tag} for a personal "
        "watchlist dashboard. 3-4 sentences: recent direction/performance, any "
        "notable news or catalysts, and a brief outlook. If it's a private "
        "company, give a business update instead of a stock price. Be factual "
        "and plain-spoken. Do not invent a specific real-time price — you don't "
        "have live market data; speak to trend and context."
    )


def _claude_update(name: str, ticker: str) -> str:
    """Live Anthropic call for one stock's briefing. Real Claude text, but not
    real-time market data (see module docstring)."""
    prompt = briefing_prompt(name, ticker)
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


@router.get("/api/stocks/history")
async def get_history(symbol: str = "") -> JSONResponse:
    """Daily close history for one ticker's sparkline (lazy-loaded on expand)."""
    return JSONResponse({"points": _history(symbol)})


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


class SetBriefingIn(BaseModel):
    sector_id: str
    name: str
    ticker: str = ""
    update: str


@router.post("/api/stocks/set-briefing")
async def set_briefing(body: SetBriefingIn) -> JSONResponse:
    """Store a pre-generated briefing (no live call) — used by the daily Batch
    job, which generates every stock's briefing at 50% via the Batch API and
    writes the results back here."""
    stamp = _now()
    data = _data()
    found = False
    for sec in data["sectors"]:
        if sec.get("id") != body.sector_id:
            continue
        for st in sec["stocks"]:
            if st["name"] == body.name and (st.get("ticker") or "") == body.ticker:
                st["update"] = body.update
                st["updated_at"] = stamp
                found = True
    if found:
        store.save("stocks", data)
    return JSONResponse({"ok": found, "updated_at": stamp})


# ── Page ──────────────────────────────────────────────────────────────────────
@router.get("/stocks", response_class=HTMLResponse)
async def stocks_page(request: Request) -> HTMLResponse:
    if request.query_params.get("bare"):
        return HTMLResponse(theme.embed(_BODY))
    return HTMLResponse(theme.page("Finance & Wealth", _BODY, active="stocks"))


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
  .sector-head .expand-all { margin-left: auto; }
  .sector-head .count { font-size: 11px; font-weight: 700; color: #1a1305; background: var(--gold); border-radius: 20px; padding: 1px 9px; }
  .stocks-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(236px, 1fr)); gap: 12px; align-items: start; }
  .stock { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 12px; padding: 13px 14px; }
  .stock-top { display: flex; align-items: baseline; gap: 8px; cursor: pointer; }
  .stock-chev { color: var(--muted); font-size: 10px; transition: transform 0.15s; margin-right: 1px; align-self: center; }
  .stock.open .stock-chev { transform: rotate(90deg); }
  .stock-name { font-size: 14.5px; font-weight: 700; }
  .stock-ticker { font-size: 11px; color: var(--gold); font-weight: 700; letter-spacing: 0.06em; margin-left: auto; }
  .stock-price { margin: 7px 0 0; min-height: 16px; }
  .stock-price .px { font-size: 18px; font-weight: 700; }
  .stock-price .chg { font-size: 12px; margin-left: 7px; font-weight: 600; }
  .stock-price .chg.up { color: #80D4A0; } .stock-price .chg.down { color: #F08080; }
  .stock-price .px-none { font-size: 10.5px; color: var(--muted); }
  /* 30-day sparkline — lazy-loaded only when a card is expanded */
  .spark { display: none; margin: 11px 0 0; }
  .stock.open .spark { display: block; }
  .spark-cap { font-size: 8.5px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); margin-bottom: 3px; }
  .spark-svg { width: 100%; height: 40px; display: block; }
  .spark-msg { font-size: 11px; color: var(--muted); font-style: italic; }
  /* Briefing text is retractable — collapsed by default to keep the page compact */
  .stock-update { font-size: 13px; line-height: 1.65; color: #cdd5e8; margin: 11px 0 0; white-space: pre-wrap; display: none; }
  .stock.open .stock-update { display: block; }
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
    <h1>Finance &amp; Wealth 📈</h1>
    <button class="btn btn-sm" id="manage-btn">Manage</button>
  </div>
  <div class="cat-tabs"><a href="/nominal">&#128176; Budget</a><a href="/wealth">&#128202; Investments</a><a href="/stocks" class="active">&#128200; Stocks</a></div>
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

const skey = (sec, st) => `${sec.id}|${st.name}|${st.ticker || ""}`;
let openStocks = new Set();

function stockCard(sec, st) {
  const upd = (st.update || "").trim();
  const body = upd
    ? `<div class="stock-update">${esc(upd)}</div>`
    : '<div class="stock-update empty">No briefing yet — hit Refresh for an AI preview.</div>';
  const stamp = st.updated_at ? `<span class="stamp">Updated ${esc(fmtWhen(st.updated_at))}</span>` : '<span></span>';
  const tkr = (st.ticker || "").trim().toUpperCase();
  const px = tkr ? `<div class="stock-price" data-px="${esc(tkr)}"></div>` : "";
  const key = skey(sec, st);
  const open = openStocks.has(key) ? " open" : "";
  return `<div class="stock${open}" data-key="${esc(key)}">
    <div class="stock-top" data-toggle="${esc(key)}">
      <span class="stock-chev">▶</span>
      <span class="stock-name">${esc(st.name)}</span>
      <span class="stock-ticker">${esc(st.ticker || "")}</span>
    </div>
    ${px}
    ${tkr ? `<div class="spark" data-ticker="${esc(tkr)}"></div>` : ""}
    ${body}
    <div class="stock-foot">
      ${stamp}
      <button class="btn btn-sm refresh icon" title="Refresh briefing" data-sec="${esc(sec.id)}" data-name="${esc(st.name)}" data-ticker="${esc(st.ticker||"")}">↻</button>
    </div>
  </div>`;
}

function render() {
  renderNote();
  const v = $("#view");
  v.innerHTML = data.sectors.map(sec => `
    <div class="sector">
      <div class="sector-head"><h2>${esc(sec.name)}</h2><span class="count">${sec.stocks.length}</span><span class="preview-tag">AI preview</span>
        <button class="btn btn-sm expand-all" type="button">Expand all</button></div>
      ${sec.stocks.length
        ? `<div class="stocks-grid">${sec.stocks.map(st => stockCard(sec, st)).join("")}</div>`
        : '<div class="sector-empty">No stocks in this sector yet — use Manage to add one.</div>'}
    </div>`).join("");
  v.querySelectorAll(".refresh").forEach(b => b.addEventListener("click", onRefresh));
  // Click a card header to retract / expand its briefing.
  v.querySelectorAll("[data-toggle]").forEach(el => el.addEventListener("click", () => {
    const key = el.dataset.toggle;
    const card = el.closest(".stock");
    if (openStocks.has(key)) { openStocks.delete(key); card.classList.remove("open"); }
    else { openStocks.add(key); card.classList.add("open"); loadSpark(card); }
  }));
  // Expand all / collapse all per sector.
  v.querySelectorAll(".expand-all").forEach(btn => btn.addEventListener("click", () => {
    const cards = [...btn.closest(".sector").querySelectorAll(".stock")];
    const anyClosed = cards.some(c => !c.classList.contains("open"));
    cards.forEach(c => { if (anyClosed) { c.classList.add("open"); openStocks.add(c.dataset.key); loadSpark(c); }
                         else { c.classList.remove("open"); openStocks.delete(c.dataset.key); } });
    btn.textContent = anyClosed ? "Collapse all" : "Expand all";
  }));
  v.querySelectorAll(".stock.open").forEach(loadSpark);  // re-draw charts for cards left open
  loadQuotes();
}

// 30-day sparkline — fetched only when a card is open, cached per ticker so a
// re-render (or re-expand) is instant.
const sparkData = {};
async function loadSpark(card) {
  const el = card.querySelector(".spark");
  if (!el || el.dataset.done) return;
  const tkr = el.dataset.ticker; if (!tkr) return;
  el.dataset.done = "1";
  if (sparkData[tkr]) { el.innerHTML = renderSpark(sparkData[tkr]); return; }
  el.innerHTML = '<span class="spark-msg">loading chart…</span>';
  try {
    const res = await (await fetch("/api/stocks/history?symbol=" + encodeURIComponent(tkr))).json();
    sparkData[tkr] = res.points || [];
    el.innerHTML = renderSpark(sparkData[tkr]);
  } catch (_) { el.innerHTML = '<span class="spark-msg">chart unavailable</span>'; el.dataset.done = ""; }
}

function renderSpark(pts) {
  if (!pts || pts.length < 2) return '<span class="spark-msg">no chart data</span>';
  const w = 240, h = 40, pad = 3;
  const min = Math.min(...pts), max = Math.max(...pts), range = (max - min) || 1;
  const stepX = (w - pad * 2) / (pts.length - 1);
  const coords = pts.map((p, i) => `${(pad + i * stepX).toFixed(1)},${(pad + (h - pad * 2) * (1 - (p - min) / range)).toFixed(1)}`);
  const up = pts[pts.length - 1] >= pts[0];
  const color = up ? "#80D4A0" : "#F08080";
  const last = coords[coords.length - 1].split(",");
  return `<div class="spark-cap">30-day · close</div>
    <svg class="spark-svg" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
      <polyline points="${coords.join(" ")}" fill="none" stroke="${color}" stroke-width="1.5" vector-effect="non-scaling-stroke"/>
      <circle cx="${last[0]}" cy="${last[1]}" r="2.5" fill="${color}"/>
    </svg>`;
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
      const dol = (up ? "+" : "−") + "$" + Math.abs(q.change).toFixed(2);
      const pct = (up ? "+" : "−") + Math.abs(q.pct).toFixed(2) + "%";
      el.innerHTML = `<span class="px">$${q.price.toLocaleString()}</span> <span class="chg ${up ? "up" : "down"}">${up ? "▲" : "▼"} ${dol} · ${pct}</span>`;
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
  b.disabled = true; b.innerHTML = '<span class="spin"></span>';
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
      if (st) { st.update = out.update; st.updated_at = out.updated_at; openStocks.add(skey(sec, st)); }  // show the fresh briefing
      render();
    } else { alert(out.message || "Failed."); b.disabled = false; b.textContent = "↻"; }
  } catch (_) { b.disabled = false; b.textContent = "↻"; }
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
