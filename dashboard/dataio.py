"""Data export / import (NEO-79) — own your data, for real.

One button downloads everything this instance has stored as a single JSON file;
one button restores from it. Works on both store backends (files or Postgres)
because it goes through store.load/save. Auth/payment internals are never
exported. This is the concrete proof of the "download it, own your data" promise.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from . import profile, store, theme

router = APIRouter()

# Auth + payment internals stay out of a personal-data export.
EXCLUDE = {"users", "billing"}


def _export_dict() -> dict:
    return {k: store.load(k, None) for k in store.keys() if k not in EXCLUDE}


@router.get("/api/data/export")
async def export_data() -> Response:
    payload = {
        "app": "neo",
        "instance": profile.ACTIVE.get("key"),
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data": _export_dict(),
    }
    body = json.dumps(payload, indent=2, ensure_ascii=False)
    fname = f"{profile.ACTIVE.get('key', 'neo')}-data.json"
    return Response(body, media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@router.post("/api/data/import")
async def import_data(body: dict) -> JSONResponse:
    # Accept either the full export payload ({"data": {...}}) or a bare data dict.
    data = body.get("data") if isinstance(body, dict) and "data" in body else body
    if not isinstance(data, dict):
        return JSONResponse({"ok": False, "message": "That doesn't look like an Aria data file."}, status_code=400)
    restored = []
    for k, v in data.items():
        if k in EXCLUDE:
            continue
        store.save(k, v)
        restored.append(k)
    return JSONResponse({"ok": True, "restored": restored, "count": len(restored)})


@router.post("/api/data/delete")
async def delete_data() -> JSONResponse:
    """Erase all of the current user's content (their account login stays)."""
    deleted = store.wipe_user()
    return JSONResponse({"ok": True, "deleted": deleted, "count": len(deleted)})


@router.get("/data")
async def data_page():
    # Gentle instances hide the data tools entirely (no rabbit hole, even by URL).
    if profile.ACTIVE.get("hide_data_export"):
        return RedirectResponse("/", status_code=302)
    return HTMLResponse(theme.page("Your data", _BODY, active=""))


_BODY = r"""
<style>
  .data-wrap { max-width: 620px; margin: 10px auto; }
  .data-wrap h1 { font-size: 38px; } .data-wrap h1 b { color: var(--gold); font-weight: 400; }
  .data-wrap .sub { color: var(--muted); font-size: 13px; margin: 6px 0 24px; line-height: 1.6; }
  .data-card { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 22px; margin-bottom: 16px; }
  .data-card h2 { font-size: 18px; margin-bottom: 6px; }
  .data-card p { font-size: 13px; color: var(--muted); line-height: 1.6; margin-bottom: 14px; }
  .data-card input[type=file] { display: none; }
  #imp-result, #del-result { display:none; margin-top:14px; font-size:13px; padding:10px 12px; border-radius:10px; background: var(--gold-soft); border:1px solid var(--gold-line); color: var(--text); }
  #imp-result.show, #del-result.show { display:block; }
</style>
<main class="data-wrap">
  <h1>Your <b>data</b></h1>
  <p class="sub">Everything here is yours. Download a complete copy anytime, or restore from one. Your login and payment details aren't included — just your content.</p>

  <div class="data-card">
    <h2>⬇ Export</h2>
    <p>Download all your data as a single JSON file you keep. No account or internet required to read it — it's just yours.</p>
    <a class="btn btn-gold" href="/api/data/export">Download my data</a>
  </div>

  <div class="data-card">
    <h2>⬆ Import</h2>
    <p>Restore from a previously exported file. This <b>overwrites</b> matching data in this instance.</p>
    <label class="btn" for="imp">Choose a file…</label>
    <input type="file" id="imp" accept="application/json,.json">
    <div id="imp-result"></div>
  </div>

  <div class="data-card">
    <h2>🗑 Delete everything</h2>
    <p>Permanently erase all your content from Aria. Your login stays, but every
       module's data is deleted. <b>This can't be undone</b> — export first if you'd
       like a copy.</p>
    <button class="btn" id="del-btn" style="border-color:var(--gold-line);">Delete my data</button>
    <div id="del-result"></div>
  </div>
</main>
<script>
const res = document.getElementById("imp-result");
document.getElementById("imp").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  let payload;
  try { payload = JSON.parse(await file.text()); }
  catch (_) { show("That file isn't valid JSON.", false); e.target.value=""; return; }
  if (!confirm("Restore from this file? It will overwrite matching data in this instance.")) { e.target.value=""; return; }
  try {
    const out = await (await fetch("/api/data/import", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload) })).json();
    show(out.ok ? ("Restored " + out.count + " item(s): " + (out.restored||[]).join(", ")) : (out.message||"Import failed."), out.ok);
  } catch (_) { show("Network error during import.", false); }
  e.target.value = "";
});
function show(msg, ok){ res.textContent = msg; res.classList.add("show"); res.style.opacity = ok?1:0.9; }

const delBtn = document.getElementById("del-btn");
if (delBtn) delBtn.addEventListener("click", async () => {
  if (!confirm("Permanently delete ALL your data? This cannot be undone.")) return;
  if (!confirm("Are you absolutely sure? Everything will be erased.")) return;
  const dr = document.getElementById("del-result");
  try {
    const out = await (await fetch("/api/data/delete", { method:"POST" })).json();
    dr.textContent = out.ok ? ("Deleted " + out.count + " item(s). Your data is gone.") : "Delete failed.";
  } catch (_) { dr.textContent = "Network error during delete."; }
  dr.classList.add("show");
});
</script>
"""
