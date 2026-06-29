"""You / Settings (NEO-90) — editable identity + module show/hide.

Gentle and skippable: set what to be called, your pronouns, your age, and (on
non-locked instances) choose which modules appear. Nothing required, nothing
that nags — the #1 guardrail.

Identity lives in the store under "me" {name, pronouns, age}; profile.who()
reads it so the greeting/nav reflect the user's choice over the profile default.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from . import profile, registry, store, theme, themes

router = APIRouter()


def _me() -> dict:
    return store.load("me", {"name": "", "pronouns": "", "age": ""})


@router.get("/api/me")
async def get_me() -> JSONResponse:
    m = _me()
    return JSONResponse({"name": m.get("name", ""), "pronouns": m.get("pronouns", ""),
                         "age": m.get("age", ""), "default_name": profile.ACTIVE.get("who", "")})


class MeIn(BaseModel):
    name: str = ""
    pronouns: str = ""
    age: str = ""


@router.post("/api/me")
async def save_me(body: MeIn) -> JSONResponse:
    store.save("me", {"name": body.name.strip(), "pronouns": body.pronouns.strip(),
                      "age": str(body.age).strip()})
    return JSONResponse({"ok": True})


class ModIn(BaseModel):
    key: str = ""
    on: bool = True


@router.post("/api/me/module")
async def toggle_module(body: ModIn) -> JSONResponse:
    # Owners always have everything; locked instances are curated by the owner.
    if profile.ACTIVE.get("lock_modules") or registry.is_owner():
        return JSONResponse({"ok": False, "error": "not allowed"}, status_code=403)
    if body.on:
        registry.enable(body.key)
    else:
        registry.disable(body.key)
    return JSONResponse({"ok": True, "enabled": registry.enabled_keys()})


@router.post("/api/me/reset-modules")
async def reset_modules() -> JSONResponse:
    """Reset the shown modules to this profile's default. Data is kept."""
    if profile.ACTIVE.get("lock_modules") or registry.is_owner():
        return JSONResponse({"ok": False, "error": "not allowed"}, status_code=403)
    registry.reset_modules()
    return JSONResponse({"ok": True, "enabled": registry.enabled_keys()})


@router.get("/api/theme")
async def get_theme() -> JSONResponse:
    return JSONResponse({"current": themes.current(), "options": themes.options()})


class ThemeIn(BaseModel):
    name: str = ""


@router.post("/api/theme")
async def set_theme_api(body: ThemeIn) -> JSONResponse:
    return JSONResponse({"ok": themes.set_theme(body.name), "current": themes.current()})


@router.get("/me", response_class=HTMLResponse)
async def me_page() -> HTMLResponse:
    show_modules = "1" if (not profile.ACTIVE.get("lock_modules") and not registry.is_owner()) else ""
    return HTMLResponse(theme.page("You", _BODY.replace("<!--MODS-->", show_modules), active=""))


_BODY = r"""
<style>
  .me-wrap { max-width: 560px; margin: 10px auto; }
  .me-wrap h1 { font-size: 36px; } .me-wrap h1 b { color: var(--gold); font-weight: 400; }
  .me-wrap .sub { color: var(--muted); font-size: 13px; margin: 6px 0 22px; }
  .card { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 14px; padding: 22px; margin-bottom: 16px; }
  .card h2 { font-size: 18px; margin-bottom: 4px; } .card p { font-size: 12.5px; color: var(--muted); margin-bottom: 14px; }
  .card label { display: block; font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); margin: 12px 0 5px; }
  .card input { width: 100%; }
  .save-row { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
  #saved { font-size: 12.5px; color: var(--gold); opacity: 0; transition: opacity .2s; }
  #saved.show { opacity: 1; }
  .mod-toggle { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 11px 0; border-bottom: 1px solid var(--line-soft); }
  .mod-toggle:last-child { border-bottom: none; }
  .mod-toggle .nm { font-size: 14px; } .mod-toggle .ds { font-size: 12px; color: var(--muted); }
  .sw { position: relative; width: 42px; height: 24px; flex: none; }
  .sw input { opacity: 0; width: 0; height: 0; }
  .sw .sl { position: absolute; inset: 0; background: var(--field); border: 1px solid var(--line); border-radius: 24px; cursor: pointer; transition: .15s; }
  .sw .sl::before { content: ""; position: absolute; height: 16px; width: 16px; left: 3px; top: 3px; background: var(--muted); border-radius: 50%; transition: .15s; }
  .sw input:checked + .sl { background: var(--gold-soft); border-color: var(--gold-line); }
  .sw input:checked + .sl::before { transform: translateX(18px); background: var(--gold); }
  .theme-grid { display: flex; flex-wrap: wrap; gap: 10px; }
  .theme-sw { display: flex; align-items: center; gap: 9px; background: var(--field); border: 1px solid var(--line); border-radius: 12px; padding: 9px 13px 9px 9px; cursor: pointer; font-family: inherit; font-size: 13px; color: var(--text); transition: border-color .15s; }
  .theme-sw:hover { border-color: var(--gold-line); }
  .theme-sw.active { border-color: var(--gold); box-shadow: 0 0 0 1px var(--gold); }
  .theme-dot { width: 26px; height: 26px; border-radius: 7px; border: 1px solid rgba(127,127,127,0.25); flex: none; }
</style>
<main class="me-wrap">
  <h1>You</h1>
  <p class="sub">Make it yours. Everything's optional — change anything, anytime.</p>

  <div class="card">
    <h2>About you</h2>
    <label for="name">What should we call you?</label>
    <input id="name" type="text" placeholder="">
    <label for="pronouns">Pronouns</label>
    <input id="pronouns" type="text" placeholder="she/her">
    <label for="age">Age (optional)</label>
    <input id="age" type="text" placeholder="">
    <div class="save-row"><button class="btn btn-gold" id="save">Save</button><span id="saved">Saved ✓</span></div>
  </div>

  <div class="card">
    <h2>Theme</h2>
    <p>Pick the look that feels right today. It saves and follows you.</p>
    <div id="themes" class="theme-grid"></div>
  </div>

  <div class="card">
    <h2>Privacy lock</h2>
    <p>Add a PIN to keep <b>Wellness</b> &amp; <b>Body</b> private — they'll ask for it before opening. Off by default, and only ever your choice.</p>
    <div id="lock-off">
      <input id="lock-pin" type="password" inputmode="numeric" placeholder="4–8 digit PIN" style="max-width:200px;">
      <button class="btn btn-sm" id="lock-set" style="margin-left:8px;">Turn on lock</button>
    </div>
    <div id="lock-on" style="display:none;">
      <span style="font-size:13px;color:var(--gold);">🔒 Lock is on for Wellness &amp; Body.</span>
      <button class="btn btn-sm" id="lock-disable" style="margin-left:10px;">Turn off</button>
    </div>
    <div id="lock-msg" style="font-size:12px;color:var(--muted);margin-top:10px;"></div>
  </div>

  <div class="card" id="mods-card" style="display:none;">
    <h2>Your modules</h2>
    <p>Turn on what you'd like. Nothing's forced, and you can change it whenever.</p>
    <div id="mods"></div>
    <div style="margin-top:16px; display:flex; align-items:center; gap:12px;">
      <button class="btn btn-sm" id="reset-mods">Reset to default</button>
      <span style="font-size:12px; color:var(--muted);">Restores the default set — your data is kept.</span>
    </div>
  </div>
</main>
<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])));
const SHOW_MODS = "<!--MODS-->" === "1";

async function loadMe() {
  const m = await (await fetch("/api/me")).json();
  $("#name").value = m.name || "";
  $("#name").placeholder = m.default_name || "your name";
  $("#pronouns").value = m.pronouns || "";
  $("#age").value = m.age || "";
}
$("#save").addEventListener("click", async () => {
  await fetch("/api/me", { method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({ name:$("#name").value, pronouns:$("#pronouns").value, age:$("#age").value }) });
  const s = $("#saved"); s.classList.add("show"); setTimeout(() => s.classList.remove("show"), 1600);
});

async function loadMods() {
  if (!SHOW_MODS) return;
  $("#mods-card").style.display = "block";
  const d = await (await fetch("/api/modules")).json();
  const enabled = (d.enabled || []).map(m => ({...m, on:true}));
  const available = (d.available || []).map(m => ({...m, on:false}));
  const all = [...enabled, ...available];
  $("#mods").innerHTML = all.map(m => `
    <div class="mod-toggle">
      <div><div class="nm">${esc(m.name)}</div><div class="ds">${esc(m.description)}</div></div>
      <label class="sw"><input type="checkbox" data-key="${esc(m.key)}" ${m.on?"checked":""}><span class="sl"></span></label>
    </div>`).join("");
  $("#mods").querySelectorAll("input[data-key]").forEach(cb => cb.addEventListener("change", async () => {
    await fetch("/api/me/module", { method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ key: cb.dataset.key, on: cb.checked }) });
  }));
  const rb = $("#reset-mods");
  if (rb) rb.addEventListener("click", async () => {
    if (!confirm("Reset which modules are shown back to the default? Your data is kept.")) return;
    await fetch("/api/me/reset-modules", { method:"POST" });
    loadMods();
  });
}
async function loadThemes() {
  const d = await (await fetch("/api/theme")).json();
  const cur = d.current || "";
  $("#themes").innerHTML = (d.options || []).map(o => `
    <button class="theme-sw ${o.key===cur?'active':''}" data-key="${esc(o.key)}">
      <span class="theme-dot" style="background:linear-gradient(135deg, ${esc(o.bg)} 58%, ${esc(o.accent)} 58%)"></span>
      ${esc(o.label)}
    </button>`).join("");
  $("#themes").querySelectorAll(".theme-sw").forEach(b => b.addEventListener("click", async () => {
    await fetch("/api/theme", { method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ name: b.dataset.key }) });
    location.reload();
  }));
}
async function loadLock() {
  const d = await (await fetch('/api/lock/status')).json();
  $("#lock-off").style.display = d.on ? 'none' : 'block';
  $("#lock-on").style.display = d.on ? 'block' : 'none';
}
const lockSet = $("#lock-set");
if (lockSet) lockSet.addEventListener('click', async () => {
  const out = await (await fetch('/api/lock/set', { method:'POST', headers:{"Content-Type":"application/json"}, body: JSON.stringify({ pin: $("#lock-pin").value }) })).json();
  $("#lock-msg").textContent = out.ok ? 'Lock on — Wellness & Body now ask for your PIN.' : (out.message || 'Failed.');
  if (out.ok) { $("#lock-pin").value = ''; loadLock(); }
});
const lockOff = $("#lock-disable");
if (lockOff) lockOff.addEventListener('click', async () => {
  await fetch('/api/lock/off', { method:'POST' });
  $("#lock-msg").textContent = 'Lock off.';
  loadLock();
});
loadMe(); loadMods(); loadThemes(); loadLock();
</script>
"""
