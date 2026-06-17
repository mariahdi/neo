"""About Me (NEO-29) — the story of how NEO was built, father and daughter.

A standalone page (not the work board) with three editable sections:
a narrative, a shared photo, and a milestones timeline. Two mock roles
(Mariah, Dad) — either can edit, and we record who saved last.

Data lives in the JSON store (dashboard/data/about.json). See store.py for the
persistence caveat. The photo is kept inline as a base64 data URL so it rides
along in the same store — fine for one image; revisit if this grows.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from . import store, theme

router = APIRouter()

MAX_PHOTO_BYTES = 5 * 1024 * 1024  # 5 MB cap so the JSON store stays sane.

# Mock/placeholder content shown until someone edits it.
DEFAULT = {
    "narrative": (
        "NEO started as a father–daughter project — a way to turn the work we "
        "talk through into something we can both see, steer, and sign off on. "
        "Dad brings the domain and the judgment; I bring the build. This page "
        "is the story of how it came together.\n\n"
        "(Placeholder text — click Edit to make it yours.)"
    ),
    "photo": None,  # data URL once uploaded
    "milestones": [
        {"date": "2026-05-01", "label": "First line of NEO written"},
        {"date": "2026-06-16", "label": "Unified dashboard goes live"},
    ],
    "updated_by": None,
    "updated_at": None,
}


def _data() -> dict:
    return store.load("about", DEFAULT)


def _stamp(d: dict, role: str | None) -> None:
    d["updated_by"] = (role or "Mariah").strip() or "Mariah"
    d["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")


# ── API ───────────────────────────────────────────────────────────────────────
@router.get("/api/about")
async def get_about() -> JSONResponse:
    return JSONResponse(_data())


class AboutIn(BaseModel):
    narrative: str = ""
    milestones: list[dict] = []
    role: str | None = "Mariah"


@router.post("/api/about")
async def save_about(body: AboutIn) -> JSONResponse:
    d = _data()
    d["narrative"] = body.narrative
    # Keep only well-formed milestones (a label is required; date optional).
    d["milestones"] = [
        {"date": (m.get("date") or "").strip(), "label": (m.get("label") or "").strip()}
        for m in body.milestones
        if (m.get("label") or "").strip()
    ]
    _stamp(d, body.role)
    store.save("about", d)
    return JSONResponse(d)


@router.post("/api/about/photo")
async def upload_photo(photo: UploadFile = File(...), role: str = Form("Mariah")) -> JSONResponse:
    raw = await photo.read()
    if not raw:
        return JSONResponse({"ok": False, "message": "Empty file."}, status_code=400)
    if len(raw) > MAX_PHOTO_BYTES:
        return JSONResponse({"ok": False, "message": "Photo too large (max 5 MB)."}, status_code=400)
    ctype = photo.content_type or "image/jpeg"
    if not ctype.startswith("image/"):
        return JSONResponse({"ok": False, "message": "Please choose an image file."}, status_code=400)
    d = _data()
    d["photo"] = f"data:{ctype};base64," + base64.b64encode(raw).decode()
    _stamp(d, role)
    store.save("about", d)
    return JSONResponse({"ok": True, "photo": d["photo"]})


# ── Page ──────────────────────────────────────────────────────────────────────
@router.get("/about", response_class=HTMLResponse)
async def about_page() -> HTMLResponse:
    return HTMLResponse(theme.page("About", _BODY, active="about"))


_BODY = r"""
<style>
  .about-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; flex-wrap: wrap; margin-bottom: 8px; }
  .about-head h1 { font-size: 40px; }
  .about-head h1 b { color: var(--gold); font-weight: 400; }
  .role { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--muted); }
  .saved { font-size: 12px; color: var(--muted); margin: 2px 0 26px; min-height: 16px; }
  .saved b { color: var(--gold); font-weight: 600; }
  .grid { display: grid; grid-template-columns: 280px 1fr; gap: 22px; align-items: start; }
  @media (max-width: 740px) { .grid { grid-template-columns: 1fr; } }
  .photo-card { text-align: center; }
  .photo-frame { width: 100%; aspect-ratio: 4 / 5; border-radius: 12px; overflow: hidden; background: var(--field); border: 1px solid var(--line); display: flex; align-items: center; justify-content: center; }
  .photo-frame img { width: 100%; height: 100%; object-fit: cover; }
  .photo-frame .ph { color: #4f5d7e; font-size: 12px; padding: 20px; }
  .photo-card label.btn { display: inline-block; margin-top: 12px; }
  .photo-card input[type=file] { display: none; }
  .narrative { white-space: pre-wrap; font-size: 14px; line-height: 1.8; color: #cdd5e8; }
  .narrative-edit { width: 100%; min-height: 200px; resize: vertical; line-height: 1.7; }
  .ms-list { list-style: none; display: flex; flex-direction: column; gap: 0; }
  .ms-item { display: flex; gap: 14px; padding: 12px 0; border-bottom: 1px solid var(--line-soft); }
  .ms-item:last-child { border-bottom: none; }
  .ms-date { color: var(--gold); font-size: 12.5px; font-weight: 600; white-space: nowrap; min-width: 92px; }
  .ms-label { font-size: 13.5px; }
  .ms-row { display: flex; gap: 8px; margin-bottom: 8px; align-items: center; }
  .ms-row input.d { width: 150px; }
  .ms-row input.l { flex: 1; }
  .ms-row .btn { padding: 6px 10px; }
  .actions { display: flex; gap: 10px; margin-top: 16px; }
  .sec-actions { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
  .empty { color: #56638a; font-style: italic; font-size: 13px; }
</style>

<main>
  <div class="about-head">
    <h1>Our <b>Story</b></h1>
    <div class="role">
      Editing as
      <select id="role">
        <option>Mariah</option>
        <option>Dad</option>
      </select>
    </div>
  </div>
  <div class="saved" id="saved"></div>

  <div class="grid">
    <!-- Photo -->
    <div class="card photo-card">
      <div class="photo-frame" id="photo-frame"><span class="ph">No photo yet</span></div>
      <label class="btn btn-sm" for="photo-input">📷 Upload photo</label>
      <input type="file" id="photo-input" accept="image/*">
    </div>

    <!-- Narrative + milestones -->
    <div style="display:flex;flex-direction:column;gap:22px;">
      <div class="card">
        <div class="sec-actions">
          <div class="section-label" style="margin:0;">The story</div>
          <button class="btn btn-sm" id="edit-narrative">Edit</button>
        </div>
        <div class="narrative" id="narrative-view"></div>
        <textarea class="narrative-edit" id="narrative-edit" style="display:none;"></textarea>
        <div class="actions" id="narrative-actions" style="display:none;">
          <button class="btn btn-gold btn-sm" id="save-narrative">Save</button>
          <button class="btn btn-sm" id="cancel-narrative">Cancel</button>
        </div>
      </div>

      <div class="card">
        <div class="sec-actions">
          <div class="section-label" style="margin:0;">Milestones</div>
          <button class="btn btn-sm" id="edit-ms">Edit</button>
        </div>
        <ul class="ms-list" id="ms-view"></ul>
        <div id="ms-edit" style="display:none;">
          <div id="ms-rows"></div>
          <button class="btn btn-sm" id="ms-add" style="margin-top:6px;">+ Add milestone</button>
          <div class="actions">
            <button class="btn btn-gold btn-sm" id="save-ms">Save</button>
            <button class="btn btn-sm" id="cancel-ms">Cancel</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</main>

<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])));
let data = { narrative: "", photo: null, milestones: [], updated_by: null, updated_at: null };

// Mock role — remembered in the browser, sent with every save.
const roleSel = $("#role");
roleSel.value = localStorage.getItem("neo-role") || "Mariah";
roleSel.addEventListener("change", () => localStorage.setItem("neo-role", roleSel.value));
const role = () => roleSel.value;

function fmtDate(iso) {
  if (!iso) return "";
  const m = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const p = String(iso).split("-");
  if (p.length < 3) return iso;
  const mo = m[parseInt(p[1],10)-1];
  return mo ? `${mo} ${parseInt(p[2],10)}, ${p[0]}` : iso;
}

function renderSaved() {
  const el = $("#saved");
  if (data.updated_by && data.updated_at) {
    el.innerHTML = `Last edited by <b>${esc(data.updated_by)}</b> · ${esc(fmtDate(data.updated_at.slice(0,10)))}`;
  } else { el.textContent = ""; }
}

function renderPhoto() {
  const f = $("#photo-frame");
  f.innerHTML = data.photo
    ? `<img src="${data.photo}" alt="Mariah and Dad">`
    : '<span class="ph">No photo yet</span>';
}

function renderNarrative() { $("#narrative-view").textContent = data.narrative || ""; }

function renderMilestones() {
  const v = $("#ms-view");
  if (!data.milestones.length) { v.innerHTML = '<li class="empty">No milestones yet.</li>'; return; }
  v.innerHTML = data.milestones.map(m => `
    <li class="ms-item">
      <span class="ms-date">${esc(fmtDate(m.date)) || "—"}</span>
      <span class="ms-label">${esc(m.label)}</span>
    </li>`).join("");
}

function render() { renderPhoto(); renderNarrative(); renderMilestones(); renderSaved(); }

async function load() {
  try { data = await (await fetch("/api/about")).json(); } catch (_) {}
  render();
}

async function postJSON(url, body) {
  const r = await fetch(url, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(body) });
  return r.json();
}

// ── Narrative edit ──
$("#edit-narrative").addEventListener("click", () => {
  $("#narrative-edit").value = data.narrative || "";
  $("#narrative-view").style.display = "none";
  $("#narrative-edit").style.display = "block";
  $("#narrative-actions").style.display = "flex";
  $("#edit-narrative").style.display = "none";
  $("#narrative-edit").focus();
});
function closeNarrative() {
  $("#narrative-view").style.display = "block";
  $("#narrative-edit").style.display = "none";
  $("#narrative-actions").style.display = "none";
  $("#edit-narrative").style.display = "inline-block";
}
$("#cancel-narrative").addEventListener("click", closeNarrative);
$("#save-narrative").addEventListener("click", async () => {
  data = await postJSON("/api/about", { narrative: $("#narrative-edit").value, milestones: data.milestones, role: role() });
  render(); closeNarrative();
});

// ── Milestones edit ──
function msRow(m = {date:"", label:""}) {
  const row = document.createElement("div");
  row.className = "ms-row";
  row.innerHTML = `<input class="d" type="date" value="${esc(m.date)}">
                   <input class="l" type="text" placeholder="What happened?" value="${esc(m.label)}">
                   <button class="btn btn-sm" type="button">✕</button>`;
  row.querySelector("button").addEventListener("click", () => row.remove());
  return row;
}
$("#edit-ms").addEventListener("click", () => {
  const rows = $("#ms-rows"); rows.innerHTML = "";
  (data.milestones.length ? data.milestones : [{date:"",label:""}]).forEach(m => rows.appendChild(msRow(m)));
  $("#ms-view").style.display = "none";
  $("#ms-edit").style.display = "block";
  $("#edit-ms").style.display = "none";
});
function closeMs() {
  $("#ms-view").style.display = "flex";
  $("#ms-edit").style.display = "none";
  $("#edit-ms").style.display = "inline-block";
}
$("#cancel-ms").addEventListener("click", closeMs);
$("#ms-add").addEventListener("click", () => $("#ms-rows").appendChild(msRow()));
$("#save-ms").addEventListener("click", async () => {
  const milestones = [...document.querySelectorAll("#ms-rows .ms-row")].map(r => ({
    date: r.querySelector(".d").value, label: r.querySelector(".l").value.trim(),
  })).filter(m => m.label);
  data = await postJSON("/api/about", { narrative: data.narrative, milestones, role: role() });
  render(); closeMs();
});

// ── Photo upload ──
$("#photo-input").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("photo", file);
  fd.append("role", role());
  const r = await fetch("/api/about/photo", { method: "POST", body: fd });
  const out = await r.json();
  if (out.ok) { await load(); }
  else { alert(out.message || "Upload failed."); }
  e.target.value = "";
});

load();
</script>
"""
