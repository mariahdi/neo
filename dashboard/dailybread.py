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

import os
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

from . import store, theme

router = APIRouter()

ANTHROPIC_KEY = os.environ.get("NEO_ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.environ.get("NEO_ANTHROPIC_MODEL", "claude-sonnet-4-6")

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


DEFAULT = {"photos": [], "prayers": []}  # scripture is seeded in code, not stored


def _data() -> dict:
    d = store.load("dailybread", DEFAULT)
    for k in ("photos", "prayers"):
        d.setdefault(k, [])
    return d


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

(async () => {
  try { pack = await (await fetch("/api/daily-bread/scripture")).json(); } catch (_) {}
  if (pack.today) showVerse(pack.today, true);
})();
</script>
"""