"""Recipes — a gentle recipe companion, tuned for gut health + nausea.

Built first for Nessa's instance: calm, no pressure, no streaks, nothing that
nags. Every recipe — the seeded samples and the ones you add — lives in the same
editable list, so you can edit or delete any of them. Bookmarked recipes carry a
url (and a preview image) and open the source; full recipes expand in place.

A fresh instance auto-populates with a couple of sample recipes (in the exact
same format as a personal one) so the page is never empty and the format is
obvious. They're seeded once into the editable store, then they're yours.
"""
from __future__ import annotations

import json
import re
import requests
from pathlib import Path
from urllib.parse import urljoin

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from . import profile, store, theme

router = APIRouter()

# Seeded once into the editable store on first load — gentle, gut-friendly
# examples in the same shape as a user-added recipe (so they can be edited).
SEED_RECIPES = [
    {"id": "seed-ginger-oats", "title": "Ginger & Banana Oatmeal", "time": "10 min",
     "tags": ["Gentle", "Nausea-friendly"],
     "ingredients": ["1/2 cup rolled oats", "1 cup water or milk", "1/2 banana, sliced",
                     "pinch fresh grated ginger", "drizzle of honey"],
     "steps": ["Simmer the oats in the water/milk on low until soft, ~5 min.",
               "Stir in the ginger near the end.", "Top with banana and a little honey."],
     "note": "A kind way to start a slow morning. (Edit me — make it yours.)", "url": "", "image": ""},
    {"id": "seed-quiche", "title": "Veggie Quiche", "time": "50 min",
     "tags": ["Comforting", "Gut-friendly"],
     "ingredients": ["1 pie crust", "4 eggs", "1 cup milk", "handful spinach",
                     "1/2 cup shredded cheese", "salt + pepper"],
     "steps": ["Heat oven to 375F.", "Whisk eggs + milk, stir in spinach and cheese.",
               "Pour into the crust, bake ~35-40 min until set.", "Cool a few minutes before slicing."],
     "note": "A sample recipe in the same format you'll use for your own.", "url": "", "image": ""},
    {"id": "seed-smoothie", "title": "Ginger-Banana Smoothie", "time": "5 min",
     "tags": ["Nausea-friendly", "Quick"],
     "ingredients": ["1 banana", "1/2 cup yogurt", "tiny piece fresh ginger",
                     "a few ice cubes", "drizzle of honey"],
     "steps": ["Blend everything until smooth.", "Sip slowly."],
     "note": "Cold and gentle when chewing feels like too much.", "url": "", "image": ""},
    {"id": "seed-congee", "title": "Soft Rice Congee", "time": "30 min",
     "tags": ["Gentle", "Nausea-friendly"],
     "ingredients": ["1/2 cup white rice", "4 cups water or light broth", "pinch of salt",
                     "optional: a slice of ginger"],
     "steps": ["Rinse the rice.", "Simmer low, stirring now and then, until creamy ~25 min.",
               "Salt to taste; keep it as thin as feels good."],
     "note": "The classic feel-better bowl.", "url": "", "image": ""},
    {"id": "seed-broth", "title": "Soothing Veggie Broth", "time": "25 min",
     "tags": ["Gentle", "Gut-friendly"],
     "ingredients": ["1 carrot", "1 celery stalk", "1/2 onion", "1 slice ginger",
                     "5 cups water", "pinch of salt"],
     "steps": ["Roughly chop everything.", "Simmer ~20 min.", "Strain and sip warm."],
     "note": "Sip slowly when food feels like too much.", "url": "", "image": ""},
    {"id": "seed-tea", "title": "Ginger-Peppermint Tea", "time": "5 min",
     "tags": ["Nausea-friendly", "Soothing"],
     "ingredients": ["a few slices fresh ginger", "fresh or dried peppermint", "hot water", "honey"],
     "steps": ["Steep the ginger + peppermint in hot water 5 min.", "Add honey to taste."],
     "note": "Classic tummy-settlers — warm and quiet.", "url": "", "image": ""},
]


_SEEDS_DIR = Path(__file__).resolve().parent / "seeds"


def _profile_seed_recipes() -> list:
    """Extra starter recipes bundled for a specific instance (e.g. Nessie's),
    named by the profile's `seed_recipes`. Empty for instances that don't set it."""
    fname = profile.ACTIVE.get("seed_recipes")
    if not fname:
        return []
    try:
        return json.loads((_SEEDS_DIR / fname).read_text(encoding="utf-8"))
    except Exception:
        return []


def _data() -> dict:
    d = store.load("recipes", {"added": [], "favs": [], "seeded": False})
    d.setdefault("added", [])
    d.setdefault("favs", [])
    have = {(r.get("title") or "").strip().lower() for r in d["added"]}
    changed = False

    def _seed(items):
        nonlocal changed
        for s in items:
            t = (s.get("title") or "").strip().lower()
            if t and t not in have:
                d["added"].append(dict(s))
                have.add(t)
                changed = True

    # Base samples once; then any instance-bundled seeds once — tracked
    # separately so the extras still land on an account seeded before they shipped.
    if not d.get("seeded"):
        _seed(SEED_RECIPES)
        d["seeded"] = True
        changed = True
    if profile.ACTIVE.get("seed_recipes") and not d.get("seeded_profile"):
        _seed(_profile_seed_recipes())
        d["seeded_profile"] = True
        changed = True
    if changed:
        store.save("recipes", d)
    return d


# ── API ───────────────────────────────────────────────────────────────────────
@router.get("/api/recipes")
async def get_recipes() -> JSONResponse:
    d = _data()
    return JSONResponse({"added": d["added"], "favs": d["favs"]})


class RecipesIn(BaseModel):
    added: list[dict] = []
    favs: list[str] = []


_IMG_PATTERNS = (
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    r'<meta[^>]+name=["\']twitter:image(?::src)?["\'][^>]+content=["\']([^"\']+)["\']',
    r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\']',
)


def _og_image(url: str) -> str:
    """Best-effort: a web page's preview image (og:image / twitter:image).
    Returns an absolute URL, or "" on any failure."""
    if not url.startswith(("http://", "https://")):
        return ""
    try:
        resp = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0 (compatible; NeoBot/1.0)"})
        html = resp.text[:200_000]
    except Exception:
        return ""
    for pat in _IMG_PATTERNS:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            return urljoin(url, m.group(1).strip())
    return ""


@router.post("/api/recipes")
async def save_recipes(body: RecipesIn) -> JSONResponse:
    """Replace the full recipe list + favorites (covers add / edit / delete).
    When a recipe has a URL but no image yet, grab the page's preview thumbnail."""
    clean = []
    fetched = 0
    for r in body.added:
        title = (r.get("title") or "").strip()
        if not title:
            continue
        rid = (r.get("id") or "r-" + (re.sub(r"[^a-z0-9]+", "-", title.lower())[:24] or "recipe"))
        url = (r.get("url") or "").strip()
        img = (r.get("image") or "").strip()
        if url and not img and fetched < 8:  # cap network calls per save
            img = await run_in_threadpool(_og_image, url)
            fetched += 1
        clean.append({
            "id": rid,
            "title": title,
            "time": (r.get("time") or "").strip(),
            "tags": [t.strip() for t in (r.get("tags") or []) if t.strip()],
            "ingredients": [i.strip() for i in (r.get("ingredients") or []) if i.strip()],
            "steps": [s.strip() for s in (r.get("steps") or []) if s.strip()],
            "note": (r.get("note") or "").strip(),
            "url": url,
            "image": img,
        })
    favs = [f for f in body.favs if isinstance(f, str)]
    # Preserve the "seeded" flag so samples don't re-appear after deletion.
    cur = store.load("recipes", {})
    data = {"added": clean, "favs": favs, "seeded": cur.get("seeded", True)}
    store.save("recipes", data)
    return JSONResponse({"added": clean, "favs": favs})


# ── Page ──────────────────────────────────────────────────────────────────────
@router.get("/recipes", response_class=HTMLResponse)
async def recipes_page() -> HTMLResponse:
    return HTMLResponse(theme.page("Recipes", _BODY, active="recipes"))


_BODY = r"""
<style>
  .r-head { padding: 4px 0 8px; }
  .r-head h1 { font-size: 40px; } .r-head h1 b { color: var(--gold); font-weight: 400; font-style: italic; }
  .r-sub { font-size: 13px; color: var(--muted); margin-top: 6px; line-height: 1.6; }
  .r-tools { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin: 18px 0 8px; }
  .r-search { flex: 1; min-width: 200px; }
  .chip { font-size: 12px; padding: 6px 12px; border-radius: 20px; border: 1px solid var(--line);
          background: var(--panel); color: var(--muted); cursor: pointer; white-space: nowrap; }
  .chip.on { background: var(--gold-soft); border-color: var(--gold-line); color: var(--gold); }
  .r-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 14px; }
  @media (max-width: 620px) { .r-grid { grid-template-columns: 1fr; } }
  .recipe { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 14px; padding: 18px; }
  .recipe-img { margin: -18px -18px 12px; height: 150px; overflow: hidden; border-radius: 14px 14px 0 0; background: var(--field); }
  .recipe-img img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .recipe-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
  .recipe-title { font-size: 16px; font-weight: 700; line-height: 1.3; }
  .fav { background: none; border: none; cursor: pointer; font-size: 18px; line-height: 1; padding: 2px; color: var(--muted); }
  .fav.on { color: var(--gold); }
  .recipe-time { font-size: 12px; color: var(--muted); margin-top: 4px; }
  .tags { display: flex; gap: 6px; flex-wrap: wrap; margin: 10px 0 4px; }
  .tag-pill { font-size: 10.5px; letter-spacing: 0.03em; padding: 3px 9px; border-radius: 20px; background: var(--gold-soft); color: var(--gold); }
  .recipe-note { font-size: 12.5px; color: var(--muted); line-height: 1.6; margin-top: 8px; font-style: italic; }
  .recipe-details { display: none; margin-top: 12px; border-top: 1px solid var(--line-soft); padding-top: 12px; }
  .recipe-details.show { display: block; }
  .rd-label { font-size: 10.5px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--gold); margin: 8px 0 6px; }
  .recipe-details ul, .recipe-details ol { margin: 0 0 4px 18px; font-size: 13px; line-height: 1.7; color: var(--text); }
  .recipe-actions { display: flex; gap: 8px; align-items: center; margin-top: 12px; flex-wrap: wrap; }
  .mini-act { background: none; border: none; color: var(--muted); font-size: 12px; cursor: pointer; padding: 2px; }
  .mini-act:hover { color: var(--gold); } .mini-act.del:hover { color: var(--hot); }
  .r-empty { color: var(--muted); font-style: italic; font-size: 13px; padding: 20px 2px; }
  .form-card { background: var(--panel-2); border: 1px dashed var(--line); border-radius: 14px; padding: 18px; margin: 18px 0; display: none; }
  .form-card.show { display: block; }
  .form-card h2 { font-size: 18px; margin-bottom: 12px; }
  .form-card label { display: block; font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); margin: 12px 0 5px; }
  .form-card input, .form-card textarea { width: 100%; }
  .form-card textarea { min-height: 76px; resize: vertical; }
  .form-actions { display: flex; gap: 10px; margin-top: 14px; }
  .row2 { display: grid; grid-template-columns: 1fr 160px; gap: 12px; }
  @media (max-width: 560px) { .row2 { grid-template-columns: 1fr; } }
</style>

<main>
  <div class="r-head">
    <h1>Your <b>Kitchen</b></h1>
    <p class="r-sub">Browse, search, and save the recipes you love. Edit any of them — including the samples — or add your own. 🦋</p>
  </div>

  <div class="r-tools">
    <input class="r-search" type="text" id="search" placeholder="Search recipes or ingredients…">
    <button class="chip" id="chip-fav" data-filter="fav">♥ Saved</button>
    <button class="btn btn-gold btn-sm" id="add-btn">+ Add a recipe</button>
  </div>
  <div class="r-tools" id="tag-chips"></div>

  <div class="form-card" id="recipe-form">
    <h2 id="f-heading">Add a recipe</h2>
    <div class="row2">
      <div><label>Name</label><input type="text" id="f-title" placeholder="e.g. Cozy lentil soup"></div>
      <div><label>Time</label><input type="text" id="f-time" placeholder="e.g. 20 min"></div>
    </div>
    <label>Tags (comma separated)</label>
    <input type="text" id="f-tags" placeholder="Gentle, Quick">
    <label>Ingredients (one per line)</label>
    <textarea id="f-ing" placeholder="1 cup lentils&#10;4 cups broth&#10;1 carrot"></textarea>
    <label>Steps (one per line)</label>
    <textarea id="f-steps" placeholder="Simmer everything until soft&#10;Season to taste"></textarea>
    <label>A note (optional)</label>
    <input type="text" id="f-note" placeholder="Why you love it">
    <label>Link (optional — for bookmarked recipes)</label>
    <input type="text" id="f-url" placeholder="https://…">
    <div class="form-actions">
      <button class="btn btn-gold btn-sm" id="f-save">Save</button>
      <button class="btn btn-sm" id="f-cancel">Cancel</button>
    </div>
  </div>

  <div class="r-grid" id="grid"></div>
</main>

<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])));
let added = [], favs = [];
let query = "", favOnly = false, tagFilter = "", editing = null;

function allTags() {
  const set = new Set();
  added.forEach(r => (r.tags || []).forEach(t => set.add(t)));
  return [...set];
}
function renderTagChips() {
  $("#tag-chips").innerHTML = allTags().map(t =>
    `<button class="chip ${tagFilter===t?"on":""}" data-tag="${esc(t)}">${esc(t)}</button>`).join("");
  $("#tag-chips").querySelectorAll("[data-tag]").forEach(b => b.addEventListener("click", () => {
    tagFilter = (tagFilter === b.dataset.tag) ? "" : b.dataset.tag; render();
  }));
}
function matches(r) {
  if (favOnly && !favs.includes(r.id)) return false;
  if (tagFilter && !(r.tags || []).includes(tagFilter)) return false;
  if (query) {
    const hay = (r.title + " " + (r.tags||[]).join(" ") + " " + (r.ingredients||[]).join(" ")).toLowerCase();
    if (!hay.includes(query)) return false;
  }
  return true;
}
function cssId(id){ return (window.CSS && CSS.escape) ? CSS.escape(id) : id; }

function card(r) {
  const on = favs.includes(r.id);
  const tags = (r.tags||[]).map(t => `<span class="tag-pill">${esc(t)}</span>`).join("");
  const ing = (r.ingredients||[]).map(i => `<li>${esc(i)}</li>`).join("");
  const steps = (r.steps||[]).map(s => `<li>${esc(s)}</li>`).join("");
  const hasDetails = (r.ingredients && r.ingredients.length) || (r.steps && r.steps.length);
  const action = r.url
    ? `<a class="btn btn-sm" href="${esc(r.url)}" target="_blank" rel="noopener">Open recipe ↗</a>`
    : (hasDetails ? `<button class="btn btn-sm" data-view="${esc(r.id)}">View recipe</button>` : "");
  const details = (!r.url && hasDetails)
    ? `<div class="recipe-details" id="d-${esc(r.id)}">
         <div class="rd-label">Ingredients</div><ul>${ing || "<li>—</li>"}</ul>
         <div class="rd-label">Steps</div><ol>${steps || "<li>—</li>"}</ol>
       </div>` : "";
  return `<div class="recipe">
    ${r.image ? `<div class="recipe-img"><img src="${esc(r.image)}" alt="" loading="lazy" onerror="this.closest('.recipe-img').style.display='none'"></div>` : ""}
    <div class="recipe-top">
      <div><div class="recipe-title">${esc(r.title)}</div><div class="recipe-time">${esc(r.time||"")}</div></div>
      <button class="fav ${on?"on":""}" data-fav="${esc(r.id)}" title="${on?"Saved":"Save"}">${on?"♥":"♡"}</button>
    </div>
    <div class="tags">${tags}</div>
    ${r.note ? `<div class="recipe-note">${esc(r.note)}</div>` : ""}
    <div class="recipe-actions">
      ${action}
      <button class="mini-act" data-edit="${esc(r.id)}">✎ Edit</button>
      <button class="mini-act del" data-del="${esc(r.id)}">🗑 Delete</button>
    </div>
    ${details}
  </div>`;
}

function render() {
  renderTagChips();
  $("#chip-fav").classList.toggle("on", favOnly);
  const list = added.filter(matches);
  $("#grid").innerHTML = list.length
    ? list.map(card).join("")
    : '<div class="r-empty">Nothing here yet — try a different search, or add one with “+ Add a recipe.”</div>';
  $("#grid").querySelectorAll("[data-fav]").forEach(b => b.addEventListener("click", () => toggleFav(b.dataset.fav)));
  $("#grid").querySelectorAll("[data-view]").forEach(b => b.addEventListener("click", () => $("#d-" + cssId(b.dataset.view)).classList.toggle("show")));
  $("#grid").querySelectorAll("[data-edit]").forEach(b => b.addEventListener("click", () => openForm(added.find(r => r.id === b.dataset.edit))));
  $("#grid").querySelectorAll("[data-del]").forEach(b => b.addEventListener("click", () => removeRecipe(b.dataset.del)));
}

async function save() {
  await fetch("/api/recipes", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ added, favs }) });
}
async function load() {
  try { const d = await (await fetch("/api/recipes")).json(); added = d.added || []; favs = d.favs || []; } catch (_) {}
  render();
}
async function toggleFav(id) {
  favs = favs.includes(id) ? favs.filter(f => f !== id) : [...favs, id];
  render(); await save();
}
async function removeRecipe(id) {
  const r = added.find(x => x.id === id);
  if (!confirm("Delete “" + (r ? r.title : "this recipe") + "”?")) return;
  added = added.filter(x => x.id !== id); favs = favs.filter(f => f !== id);
  render(); await save();
}

// ── Add / Edit form (shared) ──
function openForm(r) {
  editing = r ? r.id : null;
  $("#f-heading").textContent = r ? "Edit recipe" : "Add a recipe";
  $("#f-title").value = r ? (r.title||"") : "";
  $("#f-time").value = r ? (r.time||"") : "";
  $("#f-tags").value = r ? (r.tags||[]).join(", ") : "";
  $("#f-ing").value = r ? (r.ingredients||[]).join("\n") : "";
  $("#f-steps").value = r ? (r.steps||[]).join("\n") : "";
  $("#f-note").value = r ? (r.note||"") : "";
  $("#f-url").value = r ? (r.url||"") : "";
  $("#recipe-form").classList.add("show");
  $("#recipe-form").scrollIntoView({ behavior:"smooth", block:"center" });
  $("#f-title").focus();
}
function closeForm() { $("#recipe-form").classList.remove("show"); editing = null; }
$("#add-btn").addEventListener("click", () => openForm(null));
$("#f-cancel").addEventListener("click", closeForm);
$("#f-save").addEventListener("click", async () => {
  const title = $("#f-title").value.trim();
  if (!title) { $("#f-title").focus(); return; }
  const lines = (v) => v.split("\n").map(s => s.trim()).filter(Boolean);
  const prev = editing ? (added.find(x => x.id === editing) || {}) : {};
  const obj = {
    id: editing || ("mine-" + Date.now()),
    title,
    time: $("#f-time").value.trim(),
    tags: $("#f-tags").value.split(",").map(s => s.trim()).filter(Boolean),
    ingredients: lines($("#f-ing").value),
    steps: lines($("#f-steps").value),
    note: $("#f-note").value.trim(),
    url: $("#f-url").value.trim(),
    image: prev.image || "",
  };
  added = editing ? added.map(x => x.id === editing ? obj : x) : [...added, obj];
  closeForm(); render(); await save();
});

// ── Filters ──
$("#search").addEventListener("input", (e) => { query = e.target.value.trim().toLowerCase(); render(); });
$("#chip-fav").addEventListener("click", () => { favOnly = !favOnly; render(); });

load();
</script>
"""
