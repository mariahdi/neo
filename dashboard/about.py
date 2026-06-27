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
import io
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image
from pydantic import BaseModel

from . import profile, store, theme

try:  # HEIC/HEIF (Apple/iCloud) support so those photos upload + display
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pass

router = APIRouter()

MAX_PHOTO_BYTES = 15 * 1024 * 1024  # cap the raw upload; we downscale before storing.
MAX_GALLERY = 12  # cap the photo wall so the store doesn't balloon

# Mock/placeholder content shown until someone edits it.
def _default() -> dict:
    # Profiles can set a warmer opening line (about_intro); the general default
    # is unchanged for instances that don't.
    return {
        "narrative": profile.ACTIVE.get(
            "about_intro", "This is your space — click Edit to tell your story."),
        "photo": None,  # data URL once uploaded
        "gallery": [],  # list of data URLs — the photo wall
        "milestones": [],
        "updated_by": None,
        "updated_at": None,
    }


def _data() -> dict:
    return store.load("about", _default())


def _stamp(d: dict, role: str | None) -> None:
    d["updated_by"] = (role or "Mariah").strip() or "Mariah"
    d["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")


def _process_image(raw: bytes, ctype: str | None, filename: str | None) -> str | None:
    """Normalize any uploaded photo to a browser-displayable JPEG data URL.
    Handles HEIC/HEIF (iCloud) via pillow-heif and downscales big phone photos.
    Returns None if it isn't a usable image."""
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        img.thumbnail((1600, 1600))  # keep the store light
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        # Fallback: keep as-is only if it's already a web-displayable image type.
        if ctype and ctype.startswith("image/") and not ctype.endswith(("heic", "heif")):
            return f"data:{ctype};base64," + base64.b64encode(raw).decode()
        return None


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
        return JSONResponse({"ok": False, "message": "Photo too large (max 15 MB)."}, status_code=400)
    url = _process_image(raw, photo.content_type, photo.filename)
    if not url:
        return JSONResponse({"ok": False, "message": "Please choose an image file (JPG, PNG, HEIC…)."}, status_code=400)
    d = _data()
    d["photo"] = url
    _stamp(d, role)
    store.save("about", d)
    return JSONResponse({"ok": True, "photo": d["photo"]})


@router.post("/api/about/gallery")
async def upload_gallery(files: list[UploadFile] = File(...), role: str = Form("Mariah")) -> JSONResponse:
    """Append one or more photos to the wall (pick several at once)."""
    d = _data()
    gallery = d.get("gallery") or []
    added = 0
    for f in files:
        if len(gallery) >= MAX_GALLERY:
            break
        raw = await f.read()
        if not raw or len(raw) > MAX_PHOTO_BYTES:
            continue
        url = _process_image(raw, f.content_type, f.filename)
        if url:
            gallery.append(url)
            added += 1
    d["gallery"] = gallery
    _stamp(d, role)
    store.save("about", d)
    return JSONResponse({"ok": True, "gallery": gallery, "added": added})


class GalleryRm(BaseModel):
    index: int
    role: str | None = "Mariah"


@router.post("/api/about/gallery/remove")
async def remove_gallery(body: GalleryRm) -> JSONResponse:
    d = _data()
    g = d.get("gallery") or []
    if 0 <= body.index < len(g):
        g.pop(body.index)
    d["gallery"] = g
    _stamp(d, body.role)
    store.save("about", d)
    return JSONResponse({"ok": True, "gallery": g})


# ── Page ──────────────────────────────────────────────────────────────────────
@router.get("/about", response_class=HTMLResponse)
async def about_page() -> HTMLResponse:
    # Heading + the "editing as" roles come from the profile so each instance
    # can have its own About (e.g. Nessa) without changing the general default.
    heading = f'<h1>{profile.ACTIVE.get("about_heading", "Our <b>Story</b>")}</h1>'
    roles = profile.ACTIVE.get("about_roles", ["Mariah", "Dad"])
    if len(roles) <= 1:
        only = roles[0] if roles else "Me"  # single-person instances skip the picker
        roles_html = f'<div class="role" style="display:none"><select id="role"><option>{only}</option></select></div>'
    else:
        opts = "".join(f"<option>{r}</option>" for r in roles)
        roles_html = f'<div class="role">Editing as <select id="role">{opts}</select></div>'
    body = _BODY.replace("<!--HEADING-->", heading).replace("<!--ROLES-->", roles_html)
    return HTMLResponse(theme.page("About", body, active="about"))


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
  .photo-frame .ph { color: var(--muted); font-size: 12px; padding: 20px; }
  .photo-card label.btn { display: inline-block; margin-top: 12px; }
  .photo-card input[type=file] { display: none; }
  .narrative { white-space: pre-wrap; font-size: 14px; line-height: 1.8; color: var(--text); }
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
  .empty { color: var(--muted); font-style: italic; font-size: 13px; }
  .photo-wall { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px; margin-top: 4px; }
  .pw-item { position: relative; aspect-ratio: 1 / 1; border-radius: 10px; overflow: hidden; background: var(--field); border: 1px solid var(--line-soft); }
  .pw-item img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .pw-rm { position: absolute; top: 5px; right: 5px; width: 22px; height: 22px; border-radius: 50%; border: none; background: rgba(0,0,0,0.55); color: #fff; cursor: pointer; font-size: 12px; line-height: 1; }
  .photos-card input[type=file] { display: none; }
</style>

<main>
  <div class="about-head">
    <!--HEADING-->
    <!--ROLES-->
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

  <!-- Photo wall -->
  <div class="card photos-card">
    <div class="sec-actions">
      <div class="section-label" style="margin:0;">Photos</div>
      <label class="btn btn-sm" for="gallery-input">＋ Add photos</label>
    </div>
    <input type="file" id="gallery-input" accept="image/*" multiple>
    <div class="photo-wall" id="photo-wall"></div>
  </div>
</main>

<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])));
let data = { narrative: "", photo: null, gallery: [], milestones: [], updated_by: null, updated_at: null };

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
    ? `<img src="${data.photo}" alt="Your photo">`
    : '<span class="ph">No photo yet</span>';
}

function renderGallery() {
  const w = $("#photo-wall");
  const g = data.gallery || [];
  w.innerHTML = g.length
    ? g.map((src, i) => `<div class="pw-item"><img src="${src}" alt=""><button class="pw-rm" data-i="${i}" title="Remove">✕</button></div>`).join("")
    : '<div class="empty">No photos yet — add the ones that make you smile.</div>';
  w.querySelectorAll(".pw-rm").forEach(b => b.addEventListener("click", () => removePhoto(parseInt(b.dataset.i, 10))));
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

function render() { renderPhoto(); renderGallery(); renderNarrative(); renderMilestones(); renderSaved(); }

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

// ── Photo wall (multiple) ──
$("#gallery-input").addEventListener("change", async (e) => {
  const files = [...e.target.files];
  if (!files.length) return;
  const fd = new FormData();
  files.forEach(f => fd.append("files", f));
  fd.append("role", role());
  const out = await (await fetch("/api/about/gallery", { method: "POST", body: fd })).json();
  if (out.ok) { data.gallery = out.gallery; renderGallery(); }
  else { alert(out.message || "Upload failed."); }
  e.target.value = "";
});
async function removePhoto(i) {
  if (!confirm("Remove this photo?")) return;
  const out = await (await fetch("/api/about/gallery/remove", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ index: i, role: role() }) })).json();
  if (out.ok) { data.gallery = out.gallery; renderGallery(); }
}

load();
</script>
"""
