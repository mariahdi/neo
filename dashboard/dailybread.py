"""Daily Bread (NEO-75) — a faith & uplift module for Chuck's Neo instance.

A warm, personal page built as a Father's Day gift. Three sections:

1. **Scripture of the Day** — one verse per day from a seeded 14-verse pack,
   rotating automatically (stable all day, advances at midnight). A refresh
   button offers a different verse on demand. A stubbed "verse for your day"
   feature takes a theme/feeling and suggests a verse — mock for now, with the
   real Anthropic call marked TODO so it drops in cleanly later.
2. **Family Photo Wall** — upload, caption, and feature family photos.
3. **Prayer List** — a running list of people/intentions, with answered ones
   kept in their own section to look back on.

Like every module it ships ready to use: the scripture pack is seeded in code,
photos and prayers start empty and fill in through the UI. Data persists via the
store (Postgres when DATABASE_URL is set) — see store.py.
"""
from __future__ import annotations

import base64
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from . import store, theme

router = APIRouter()

ANTHROPIC_KEY = os.environ.get("NEO_ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.environ.get("NEO_ANTHROPIC_MODEL", "claude-sonnet-4-6")
MAX_PHOTO_BYTES = 5 * 1024 * 1024  # 5 MB cap — photos ride inline in the store as
                                   # base64 data URLs, same as About Me (about.py).

# ── Scripture pack ────────────────────────────────────────────────────────────
# A two-week rotation, seeded in code so the page works day one with zero setup.
# Themes: strength, courage, family, gratitude, peace, trust, hope. (NIV.)
VERSES = [
    {"text": "I can do all this through him who gives me strength.",
     "ref": "Philippians 4:13"},
    {"text": "Be strong and courageous. Do not be afraid; do not be discouraged, "
             "for the Lord your God will be with you wherever you go.",
     "ref": "Joshua 1:9"},
    {"text": "The Lord is my shepherd, I lack nothing.",
     "ref": "Psalm 23:1"},
    {"text": "Trust in the Lord with all your heart and lean not on your own "
             "understanding; in all your ways submit to him, and he will make "
             "your paths straight.",
     "ref": "Proverbs 3:5-6"},
    {"text": "And we know that in all things God works for the good of those who "
             "love him, who have been called according to his purpose.",
     "ref": "Romans 8:28"},
    {"text": "But those who hope in the Lord will renew their strength. They will "
             "soar on wings like eagles; they will run and not grow weary, they "
             "will walk and not be faint.",
     "ref": "Isaiah 40:31"},
    {"text": "“For I know the plans I have for you,” declares the Lord, "
             "“plans to prosper you and not to harm you, plans to give you "
             "hope and a future.”",
     "ref": "Jeremiah 29:11"},
    {"text": "Give thanks to the Lord, for he is good; his love endures forever.",
     "ref": "Psalm 107:1"},
    {"text": "But as for me and my household, we will serve the Lord.",
     "ref": "Joshua 24:15"},
    {"text": "Peace I leave with you; my peace I give you. I do not give to you as "
             "the world gives. Do not let your hearts be troubled and do not be "
             "afraid.",
     "ref": "John 14:27"},
    {"text": "Cast all your anxiety on him because he cares for you.",
     "ref": "1 Peter 5:7"},
    {"text": "Love is patient, love is kind. It does not envy, it does not boast, "
             "it is not proud.",
     "ref": "1 Corinthians 13:4"},
    {"text": "The Lord bless you and keep you; the Lord make his face shine on you "
             "and be gracious to you.",
     "ref": "Numbers 6:24-25"},
    {"text": "She is clothed with strength and dignity; she can laugh at the days "
             "to come.",
     "ref": "Proverbs 31:25"},
]


def _verse_of_day(now: datetime | None = None) -> dict:
    """Today's verse — deterministic by day-of-year so it's stable all day and
    advances on its own at midnight, identical for everyone with no stored state."""
    now = now or datetime.now(timezone.utc)
    return VERSES[now.timetuple().tm_yday % len(VERSES)]


# scripture is seeded in code; photos/prayers persist. `pinned` is a photo id
# that overrides the daily featured rotation when set.
DEFAULT = {"photos": [], "prayers": [], "pinned": None}


def _id() -> str:
    return uuid.uuid4().hex[:8]


def _data() -> dict:
    d = store.load("dailybread", DEFAULT)
    for k in ("photos", "prayers"):
        d.setdefault(k, [])
    d.setdefault("pinned", None)
    return d


def _featured_id(d: dict, now: datetime | None = None) -> str | None:
    """The photo featured today: the pinned one if set & present, else a daily
    rotation by day-of-year (stable all day, advances at midnight)."""
    photos = d.get("photos") or []
    if not photos:
        return None
    pinned = d.get("pinned")
    if pinned and any(p["id"] == pinned for p in photos):
        return pinned
    now = now or datetime.now(timezone.utc)
    return photos[now.timetuple().tm_yday % len(photos)]["id"]


# ── Scripture API ─────────────────────────────────────────────────────────────
@router.get("/api/daily-bread/scripture")
async def get_scripture() -> JSONResponse:
    """Today's verse plus the full pack (so the refresh button can pick another
    without a round-trip). `index` is today's position in the pack."""
    now = datetime.now(timezone.utc)
    return JSONResponse({
        "today": _verse_of_day(now),
        "index": now.timetuple().tm_yday % len(VERSES),
        "verses": VERSES,
    })


# === CLAUDE LAYER (STUB) ======================================================
# TODO (real integration): swap _mock_suggestion() for a live Anthropic call.
# Mirror stocks.py / goals.py: when ANTHROPIC_KEY is set, POST the user's theme
# to https://api.anthropic.com/v1/messages asking for one fitting Bible verse +
# a one-line note, and parse {text, ref, note} out of the response. Until then we
# return a themed pick from the seeded pack so the feature is fully usable.
# ==============================================================================
def _mock_suggestion(theme_text: str) -> dict:
    """Keyword-match the requested feeling to a seeded verse. Stand-in for the
    Anthropic call — same shape the real one will return."""
    t = (theme_text or "").lower()
    table = [
        (("strong", "strength", "tired", "weary", "weak"), "Isaiah 40:31"),
        (("afraid", "fear", "scared", "anxious", "worry", "anxiety"), "1 Peter 5:7"),
        (("peace", "calm", "rest", "troubled"), "John 14:27"),
        (("family", "home", "kids", "children"), "Joshua 24:15"),
        (("thank", "grateful", "gratitude", "blessed"), "Psalm 107:1"),
        (("lost", "future", "plan", "direction", "guidance"), "Jeremiah 29:11"),
        (("courage", "brave", "bold"), "Joshua 1:9"),
    ]
    ref = "Philippians 4:13"
    for keys, r in table:
        if any(k in t for k in keys):
            ref = r
            break
    verse = next((v for v in VERSES if v["ref"] == ref), VERSES[0])
    return {
        "text": verse["text"],
        "ref": verse["ref"],
        "note": "A verse picked for what you're carrying today.",
        "stub": True,  # flips to false once the real Anthropic call is wired in
    }


@router.post("/api/daily-bread/verse-suggestion")
async def verse_suggestion(body: dict) -> JSONResponse:
    """Suggest a verse for a typed theme or feeling. STUBBED — returns a themed
    pick from the seeded pack today; the real Anthropic call drops in above."""
    return JSONResponse(_mock_suggestion((body.get("theme") or "").strip()))


# ── Photos + prayers API ──────────────────────────────────────────────────────
@router.get("/api/daily-bread")
async def get_daily_bread() -> JSONResponse:
    """Everything stored for the page plus the computed featured photo id."""
    d = _data()
    return JSONResponse({**d, "featured_id": _featured_id(d)})


@router.post("/api/daily-bread/photo")
async def upload_photo(photo: UploadFile = File(...), caption: str = Form("")) -> JSONResponse:
    """Add one family photo. Stored inline as a base64 data URL (≤5 MB)."""
    raw = await photo.read()
    if not raw:
        return JSONResponse({"ok": False, "message": "Empty file."}, status_code=400)
    if len(raw) > MAX_PHOTO_BYTES:
        return JSONResponse({"ok": False, "message": "Photo too large (max 5 MB)."}, status_code=400)
    ctype = photo.content_type or "image/jpeg"
    if not ctype.startswith("image/"):
        return JSONResponse({"ok": False, "message": "Please choose an image file."}, status_code=400)
    d = _data()
    d["photos"].append({
        "id": _id(),
        "src": f"data:{ctype};base64," + base64.b64encode(raw).decode(),
        "caption": (caption or "").strip(),
    })
    store.save("dailybread", d)
    return JSONResponse({"ok": True, **d, "featured_id": _featured_id(d)})


@router.post("/api/daily-bread/photos")
async def save_photos(body: dict) -> JSONResponse:
    """Update photo captions, the pinned photo, and the kept set — without
    re-uploading image data. The client sends id+caption per photo it's keeping
    (removal = leaving one out); image `src` is merged from what's stored."""
    d = _data()
    by_id = {p["id"]: p for p in d["photos"]}
    kept = []
    for p in body.get("photos", []):
        existing = by_id.get(p.get("id"))
        if existing:  # ignore unknown ids; src always comes from the store
            kept.append({**existing, "caption": (p.get("caption") or "").strip()})
    d["photos"] = kept
    pinned = body.get("pinned")
    d["pinned"] = pinned if any(p["id"] == pinned for p in kept) else None
    store.save("dailybread", d)
    return JSONResponse({**d, "featured_id": _featured_id(d)})


# ── Page ──────────────────────────────────────────────────────────────────────
@router.get("/daily-bread", response_class=HTMLResponse)
async def daily_bread_page() -> HTMLResponse:
    return HTMLResponse(theme.page("Daily Bread", _BODY, active="dailybread"))


_BODY = r"""
<style>
  /* Warm accents layered over the navy theme — scripture is the hero. */
  .db-head { text-align: center; margin: 8px 0 26px; }
  .db-head h1 { font-size: 44px; }
  .db-head h1 b { color: var(--gold); font-weight: 400; }
  .db-head .sub { font-size: 12.5px; color: var(--muted); margin-top: 4px; letter-spacing: 0.04em; }

  /* Scripture hero */
  .hero {
    position: relative; text-align: center; margin: 0 auto 18px; max-width: 760px;
    background: radial-gradient(120% 140% at 50% 0%, rgba(200,168,75,0.10), rgba(200,168,75,0.02) 60%, transparent);
    border: 1px solid var(--gold-line); border-radius: 18px;
    padding: 46px 38px 34px;
  }
  .hero .eyebrow { font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase; color: var(--gold); margin-bottom: 20px; }
  .hero .verse {
    font-family: Georgia, 'Times New Roman', serif; font-size: 27px; line-height: 1.5;
    color: #f5eed9; font-weight: 400; margin: 0 auto 18px; max-width: 640px;
    text-wrap: balance;
  }
  .hero .verse::before { content: "\201C"; color: var(--gold); }
  .hero .verse::after  { content: "\201D"; color: var(--gold); }
  .hero .ref { font-size: 14px; letter-spacing: 0.06em; color: var(--gold); font-weight: 600; }
  .hero .refresh {
    background: none; border: 1px solid var(--gold-line); color: var(--gold);
    font-family: inherit; font-size: 11.5px; font-weight: 600; letter-spacing: 0.05em;
    padding: 7px 15px; border-radius: 9px; cursor: pointer; margin-top: 22px;
    transition: background 0.15s ease;
  }
  .hero .refresh:hover { background: var(--gold-soft); }
  .hero .refresh .ico { display: inline-block; }
  .hero[data-other="1"] .today-note { visibility: visible; }
  .today-note { visibility: hidden; font-size: 11px; color: var(--muted); margin-top: 12px; }
  .today-note a { color: var(--gold); cursor: pointer; text-decoration: none; border-bottom: 1px dotted var(--gold-line); }

  /* Claude "verse for your day" */
  .vfd { max-width: 760px; margin: 0 auto 14px; }
  .vfd .row { display: flex; gap: 8px; }
  .vfd input { flex: 1; }
  .vfd .out { margin-top: 12px; padding: 16px 18px; border: 1px solid var(--line-soft); border-left: 3px solid var(--gold); border-radius: 12px; background: var(--panel); display: none; }
  .vfd .out.show { display: block; }
  .vfd .out .vtext { font-family: Georgia, serif; font-size: 16px; line-height: 1.6; color: #e8e2d0; }
  .vfd .out .vref { font-size: 12.5px; color: var(--gold); font-weight: 600; margin-top: 6px; }
  .vfd .out .vnote { font-size: 11.5px; color: var(--muted); margin-top: 8px; font-style: italic; }
  .vfd .out .stub-tag { display: inline-block; font-size: 9px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); border: 1px solid var(--line); border-radius: 8px; padding: 1px 6px; margin-left: 6px; vertical-align: 2px; }

  /* Family photo wall */
  .wall-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 34px 0 12px; flex-wrap: wrap; }
  .wall-head .section-label { margin: 0; }
  .wall-head label.btn { display: inline-block; }
  .wall-head input[type=file] { display: none; }
  .featured { margin-bottom: 18px; }
  .featured .frame { position: relative; width: 100%; max-height: 420px; aspect-ratio: 16 / 9; border-radius: 16px; overflow: hidden; border: 1px solid var(--gold-line); background: var(--field); }
  .featured .frame img { width: 100%; height: 100%; object-fit: cover; }
  .featured .badge { position: absolute; top: 12px; left: 12px; background: var(--gold); color: var(--on-gold); font-size: 10px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; padding: 4px 10px; border-radius: 20px; }
  .featured .cap { position: absolute; left: 0; right: 0; bottom: 0; padding: 28px 16px 12px; background: linear-gradient(transparent, rgba(6,9,18,0.85)); color: #f0ead8; font-size: 14px; font-family: Georgia, serif; }
  .pgrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; }
  .pcard { position: relative; border-radius: 12px; overflow: hidden; border: 1px solid var(--line-soft); background: var(--panel); }
  .pcard.is-featured { border-color: var(--gold-line); }
  .pcard .pimg { width: 100%; aspect-ratio: 1 / 1; object-fit: cover; display: block; }
  .pcard .pcap { width: 100%; box-sizing: border-box; background: transparent; border: none; border-top: 1px solid var(--line-soft); color: #cdd5e8; font-family: inherit; font-size: 12px; padding: 7px 9px; }
  .pcard .pcap:focus { outline: none; background: var(--field); }
  .pcard .ptools { position: absolute; top: 6px; right: 6px; display: flex; gap: 5px; opacity: 0; transition: opacity 0.12s ease; }
  .pcard:hover .ptools { opacity: 1; }
  .ptools button { width: 26px; height: 26px; border-radius: 7px; border: none; cursor: pointer; font-size: 12px; background: rgba(6,9,18,0.78); color: #e9ecf4; display: flex; align-items: center; justify-content: center; }
  .ptools .pin.on { background: var(--gold); color: var(--on-gold); }
  .ptools .rm:hover { background: #F08080; color: #1a1305; }
  .wall-empty { color: #56638a; font-style: italic; font-size: 13px; padding: 18px 0; text-align: center; border: 1px dashed var(--line-soft); border-radius: 12px; }
</style>

<main class="db">
  <div class="db-head">
    <h1>Daily <b>Bread</b></h1>
    <div class="sub">a verse, the faces you love, and the ones you're praying for</div>
  </div>

  <!-- Scripture hero -->
  <section class="hero" id="hero" data-other="0">
    <div class="eyebrow" id="hero-eyebrow">Scripture of the Day</div>
    <p class="verse" id="verse">&hellip;</p>
    <div class="ref" id="ref"></div>
    <button class="refresh" id="refresh"><span class="ico">&#10227;</span> Another verse</button>
    <div class="today-note"><a id="back-today">&larr; back to today's verse</a></div>
  </section>

  <!-- Claude: verse for your day (stub) -->
  <section class="vfd card">
    <div class="section-label">A verse for your day</div>
    <div class="row">
      <input id="vfd-in" type="text" placeholder="How are you feeling? e.g. tired, grateful, worried about the kids&hellip;">
      <button class="btn btn-gold btn-sm" id="vfd-go">Find a verse</button>
    </div>
    <div class="out" id="vfd-out">
      <div class="vtext" id="vfd-text"></div>
      <div class="vref" id="vfd-ref"></div>
      <div class="vnote" id="vfd-note"></div>
    </div>
  </section>

  <!-- Family photo wall -->
  <section>
    <div class="wall-head">
      <div class="section-label">Family</div>
      <label class="btn btn-sm" for="photo-input">📷 Add photo</label>
      <input type="file" id="photo-input" accept="image/*">
    </div>
    <div class="featured" id="featured" style="display:none;">
      <div class="frame">
        <span class="badge">Featured today</span>
        <img id="featured-img" alt="Featured family photo">
        <div class="cap" id="featured-cap" style="display:none;"></div>
      </div>
    </div>
    <div class="pgrid" id="pgrid"></div>
    <div class="wall-empty" id="wall-empty">No photos yet — add the faces you love.</div>
  </section>
</main>

<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])));

let pack = { today: null, index: 0, verses: [] };

function showVerse(v, isToday) {
  $("#verse").innerHTML = esc(v.text);
  $("#ref").textContent = v.ref;
  $("#hero-eyebrow").textContent = isToday ? "Scripture of the Day" : "Another verse";
  $("#hero").dataset.other = isToday ? "0" : "1";
}

function anotherVerse() {
  if (pack.verses.length < 2) return;
  const cur = $("#ref").textContent;
  let pick;
  do { pick = pack.verses[Math.floor(Math.random() * pack.verses.length)]; }
  while (pick.ref === cur);          // never repeat the one already showing
  showVerse(pick, false);
}

$("#refresh").addEventListener("click", anotherVerse);
$("#back-today").addEventListener("click", () => pack.today && showVerse(pack.today, true));

// Claude verse-for-your-day (stub)
async function findVerse() {
  const theme = $("#vfd-in").value.trim();
  if (!theme) return;
  $("#vfd-go").disabled = true;
  try {
    const r = await fetch("/api/daily-bread/verse-suggestion", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ theme }),
    });
    const v = await r.json();
    $("#vfd-text").innerHTML = "&ldquo;" + esc(v.text) + "&rdquo;";
    $("#vfd-ref").innerHTML = esc(v.ref) + (v.stub ? '<span class="stub-tag">preview</span>' : "");
    $("#vfd-note").textContent = v.note || "";
    $("#vfd-out").classList.add("show");
  } catch (_) {} finally { $("#vfd-go").disabled = false; }
}
$("#vfd-go").addEventListener("click", findVerse);
$("#vfd-in").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); findVerse(); } });

// ── Family photo wall ──
let db = { photos: [], prayers: [], pinned: null, featured_id: null };

function renderPhotos() {
  const photos = db.photos || [];
  const empty = $("#wall-empty"), feat = $("#featured");
  empty.style.display = photos.length ? "none" : "block";
  // Featured banner
  const fp = photos.find(p => p.id === db.featured_id);
  if (fp) {
    feat.style.display = "block";
    $("#featured-img").src = fp.src;
    const fc = $("#featured-cap");
    if (fp.caption) { fc.textContent = fp.caption; fc.style.display = "block"; }
    else { fc.style.display = "none"; }
  } else { feat.style.display = "none"; }
  // Grid
  $("#pgrid").innerHTML = photos.map(p => `
    <div class="pcard ${p.id === db.featured_id ? "is-featured" : ""}">
      <img class="pimg" src="${p.src}" alt="${esc(p.caption) || "Family photo"}">
      <div class="ptools">
        <button class="pin ${p.id === db.pinned ? "on" : ""}" data-pin="${esc(p.id)}" title="${p.id === db.pinned ? "Unpin" : "Pin as featured"}">📌</button>
        <button class="rm" data-rm="${esc(p.id)}" title="Remove">✕</button>
      </div>
      <input class="pcap" data-cap="${esc(p.id)}" value="${esc(p.caption)}" placeholder="Add a name or note…">
    </div>`).join("");

  $("#pgrid").querySelectorAll("[data-cap]").forEach(el => el.addEventListener("change", () => {
    const p = db.photos.find(x => x.id === el.dataset.cap); if (p) { p.caption = el.value; savePhotos(); }
  }));
  $("#pgrid").querySelectorAll("[data-pin]").forEach(el => el.addEventListener("click", () => {
    db.pinned = (db.pinned === el.dataset.pin) ? null : el.dataset.pin; savePhotos();
  }));
  $("#pgrid").querySelectorAll("[data-rm]").forEach(el => el.addEventListener("click", () => {
    db.photos = db.photos.filter(x => x.id !== el.dataset.rm);
    if (db.pinned === el.dataset.rm) db.pinned = null;
    savePhotos();
  }));
}

async function savePhotos() {
  const payload = { photos: db.photos.map(p => ({ id: p.id, caption: p.caption })), pinned: db.pinned };
  try {
    const r = await fetch("/api/daily-bread/photos", {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload),
    });
    db = await r.json();
  } catch (_) {}
  renderPhotos();
}

$("#photo-input").addEventListener("change", async (e) => {
  const file = e.target.files[0]; if (!file) return;
  const fd = new FormData(); fd.append("photo", file);
  try {
    const r = await fetch("/api/daily-bread/photo", { method: "POST", body: fd });
    const out = await r.json();
    if (out.ok) { db = out; renderPhotos(); } else { alert(out.message || "Upload failed."); }
  } catch (_) { alert("Upload failed."); }
  e.target.value = "";
});

(async () => {
  try { pack = await (await fetch("/api/daily-bread/scripture")).json(); } catch (_) {}
  if (pack.today) showVerse(pack.today, true);
  try { db = await (await fetch("/api/daily-bread")).json(); } catch (_) {}
  renderPhotos();
})();
</script>
"""