"""Module catalog (NEO-37) — API + the /modules page.

Lets a member (dad) see what modules are available, opt into new ones, and
clears the "new" badge once they've looked. An owner (Aria) sees everything
already enabled, so the page just confirms what's active.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from . import profile, registry, theme

router = APIRouter()


@router.get("/api/modules")
async def get_modules() -> JSONResponse:
    return JSONResponse({
        "role": profile.ACTIVE.get("role"),
        "enabled": registry.enabled_modules(),
        "available": registry.available_modules(),
    })


class EnableIn(BaseModel):
    key: str


@router.post("/api/modules/enable")
async def enable_module(body: EnableIn) -> JSONResponse:
    if profile.ACTIVE.get("lock_modules"):
        return JSONResponse({"ok": False, "error": "locked"}, status_code=403)
    registry.enable(body.key)
    return JSONResponse({"ok": True, "enabled": [m["key"] for m in registry.enabled_modules()]})


@router.post("/api/modules/seen")
async def mark_seen() -> JSONResponse:
    registry.mark_seen(date.today().isoformat())
    return JSONResponse({"ok": True})


@router.get("/modules")
async def modules_page():
    # Locked instances (e.g. Nessa) can't reach the catalog even by URL.
    if profile.ACTIVE.get("lock_modules"):
        return RedirectResponse("/", status_code=302)
    return HTMLResponse(theme.page("Modules", _BODY, active="modules"))


_BODY = r"""
<style>
  .mods-head h1 { font-size: 40px; } .mods-head h1 b { color: var(--gold); font-weight: 400; }
  .mods-sub { font-size: 12.5px; color: var(--muted); margin: 2px 0 26px; }
  .mods-section { font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--gold); margin: 28px 0 12px; display: flex; align-items: center; gap: 10px; }
  .mods-section .n { font-size: 11px; color: var(--on-gold); background: var(--gold); border-radius: 10px; padding: 0 7px; }
  .mod { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 12px; padding: 16px 18px; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between; gap: 14px; }
  .mod.enabled { border-left: 3px solid var(--gold); }
  .mod-info { flex: 1; }
  .mod-name { font-size: 15px; font-weight: 700; color: var(--text); display: flex; align-items: center; gap: 9px; }
  .mod-desc { font-size: 12.5px; color: var(--muted); margin-top: 4px; }
  .mod-warn { font-size: 11px; color: var(--hot); margin-top: 5px; }
  .tag-new { font-size: 9px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--on-gold); background: var(--gold); border-radius: 20px; padding: 2px 8px; }
  .mod-on { font-size: 12px; color: var(--gold); font-weight: 600; white-space: nowrap; }
  .empty { color: var(--muted); font-style: italic; font-size: 13px; padding: 4px 0; }
</style>

<main>
  <div class="mods-head"><h1>Modules</h1></div>
  <p class="mods-sub" id="sub"></p>
  <div id="catalog"><div class="empty">Loading…</div></div>
</main>

<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])));
let data = { role: "member", enabled: [], available: [] };

function availCard(m) {
  const isNew = m.isNew ? '<span class="tag-new">New</span>' : "";
  const warn = (m.unmet && m.unmet.length)
    ? `<div class="mod-warn">Needs ${m.unmet.map(esc).join(", ")} — set the key for this to work.</div>` : "";
  return `<div class="mod">
    <div class="mod-info">
      <div class="mod-name">${esc(m.name)} ${isNew}</div>
      <div class="mod-desc">${esc(m.description)}</div>
      ${warn}
    </div>
    <button class="btn btn-gold btn-sm enable" data-key="${esc(m.key)}">+ Enable</button>
  </div>`;
}
function enabledCard(m) {
  return `<div class="mod enabled">
    <div class="mod-info">
      <div class="mod-name">${esc(m.name)}</div>
      <div class="mod-desc">${esc(m.description)}</div>
    </div>
    <span class="mod-on">✓ Active</span>
  </div>`;
}

function render() {
  $("#sub").textContent = data.role === "owner"
    ? "You're the owner — every module is active here. New ones turn on automatically."
    : "Turn on the modules you want. New ones show up here when they're released.";
  const c = $("#catalog");
  const avail = data.available || [];
  let html = "";
  if (data.role !== "owner") {
    html += `<div class="mods-section">Available to add${avail.length ? `<span class="n">${avail.length}</span>` : ""}</div>`;
    html += avail.length ? avail.map(availCard).join("") : '<div class="empty">Nothing new — you have every module.</div>';
  }
  html += `<div class="mods-section">Active</div>`;
  html += (data.enabled || []).length ? data.enabled.map(enabledCard).join("") : '<div class="empty">No modules active yet.</div>';
  c.innerHTML = html;
  c.querySelectorAll(".enable").forEach(b => b.addEventListener("click", () => enable(b.dataset.key, b)));
}

async function enable(key, btn) {
  btn.disabled = true; btn.textContent = "Enabling…";
  await fetch("/api/modules/enable", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ key }) });
  await load();  // module jumps to Active; nav updates on next navigation
}

async function load() {
  try { data = await (await fetch("/api/modules")).json(); } catch (_) {}
  render();
}

// Opening the catalog counts as "seen" — clears the nav badge next navigation.
fetch("/api/modules/seen", { method: "POST" }).catch(() => {});
load();
</script>
"""
