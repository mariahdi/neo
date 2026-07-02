"""Shared look + page shell for the Neo dashboard's module pages.

The navy / gold / Bebas-Neue theme and the top navigation live here so About,
Stocks, Goals and Wins all feel like one app. The original work-board page in
main.py predates this and keeps its own inline CSS; it borrows nav(),
TOPNAV_CSS, footer(), EXTRA_CSS and TOUR_JS from here so the header, footer and
the interactive tour match everywhere.
"""
from __future__ import annotations

import os

from . import profile, registry, store, themes

ACTIVE = profile.ACTIVE

# (key, href, label) — extended as each module ships.
NAV_LINKS = [
    ("dashboard", "/", "Dashboard"),
    ("recipes", "/recipes", "Recipes"),
    ("nominal", "/nominal", "Nominal"),
    ("body", "/body", "Body"),
    ("wealth", "/wealth", "Wealth"),
    ("trips", "/trips", "Trips"),
    ("wellness", "/wellness", "Wellness"),
    ("career", "/career", "Career"),
    ("dailybread", "/daily-bread", "Daily Bread"),
    ("stocks", "/stocks", "Stocks"),
    ("goals", "/goals", "Goals"),
    ("wins", "/wins", "Wins"),
    ("about", "/about", "About"),
]


def nav(active: str = "") -> str:
    """The shared top bar. `active` is the key of the current page. Module links
    are gated to the instance's enabled set; a Modules link carries a badge when
    new modules are available to opt into."""
    enabled = set(registry.enabled_keys())
    links = ""
    # Work-board instances (e.g. Neo) split their Jira work into dedicated tabs —
    # USAFA / Proposals / Dev — instead of one generic "Dashboard" board.
    work_nav = ACTIVE.get("work_nav")
    if work_nav:
        for key, href, label in work_nav:
            cls = ' class="active"' if key == active else ""
            links += f'<a href="{href}"{cls}>{label}</a>'
    if not work_nav:
        dcls = ' class="active"' if active == "dashboard" else ""
        links += f'<a href="/"{dcls}>Dashboard</a>'
    # Nav mirrors the enabled modules straight from the registry, so labels
    # always match the launcher (e.g. "Finance & Wealth", not "Nominal").
    for m in registry.enabled_modules():
        cls = ' class="active"' if m["key"] == active else ""
        links += f'<a href="{m["path"]}"{cls}>{m["name"]}</a>'
    # Locked instances (e.g. Nessa) hide the catalog entirely — the owner adds
    # modules for them; they never see the "add more" surface.
    if not ACTIVE.get("lock_modules"):
        new = registry.new_count()
        badge = f'<span class="nav-badge">{new}</span>' if new else ""
        mcls = ' class="active"' if active == "modules" else ""
        links += f'<a href="/modules"{mcls}>Modules{badge}</a>'
    return (
        "<header>"
        f'<a class="brand" href="/">{ACTIVE["wordmark"]}</a>'
        f'<nav class="topnav">{links}</nav>'
        f'<div class="who">{profile.who()}</div>'
        f"{LOGOUT_BTN}"
        "</header>"
    )


# Self-contained so it works on every page without a shared script: clears the
# localStorage token, drops the session cookie server-side, returns to /login.
LOGOUT_BTN = (
    '<button class="logout" onclick="localStorage.removeItem(\'neo_session\');'
    "fetch('/api/logout',{method:'POST'}).finally(function(){location.href='/login'})\">"
    "Log out</button>"
)


# Just the nav pieces — injected into the legacy work-board page, which already
# styles header / .brand / .who itself.
TOPNAV_CSS = """
  .brand { text-decoration: none; }
  .topnav { display: flex; gap: 22px; margin-right: auto; margin-left: 10px; }
  .topnav a { font-size: 12px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); text-decoration: none; padding: 6px 0; }
  .topnav a:hover, .topnav a.active { color: var(--gold); }
  /* Sub-tabs for combined categories (e.g. Finance & Wealth: Budget/Investments/Stocks). */
  .cat-tabs { display: flex; gap: 8px; margin: 0 0 24px; flex-wrap: wrap; }
  .cat-tabs a { font-size: 12.5px; padding: 7px 15px; border-radius: 50px; border: 1px solid var(--line); color: var(--muted); text-decoration: none; background: var(--panel); }
  .cat-tabs a:hover { border-color: var(--gold-line); color: var(--text); }
  .cat-tabs a.active { background: var(--gold-soft); border-color: var(--gold-line); color: var(--gold); }
  .nav-badge { display: inline-block; background: var(--gold); color: var(--on-gold); font-size: 9px; font-weight: 700; border-radius: 10px; padding: 0 5px; margin-left: 5px; vertical-align: 1px; }
  .logout { background: none; border: 1px solid var(--line); color: var(--muted); font-family: inherit; font-size: 10.5px; letter-spacing: 0.1em; text-transform: uppercase; cursor: pointer; border-radius: 8px; padding: 5px 11px; }
  .logout:hover { border-color: var(--gold-line); color: var(--gold); }
  /* Mobile: keep the whole nav reachable instead of overflowing off-screen. */
  @media (max-width: 720px) {
    header { gap: 12px; padding: 14px 16px; }
    .brand { font-size: 24px; }
    .who { display: none; }
    .topnav { gap: 16px; margin-left: 4px; overflow-x: auto; white-space: nowrap;
              -webkit-overflow-scrolling: touch; scrollbar-width: none; }
    .topnav::-webkit-scrollbar { display: none; }
  }
"""

# Full shared stylesheet for new module pages. The :root block + all colors and
# fonts come from the active profile's tokens, so the same CSS themes every
# instance (Neo navy/gold, Aria warm) with no per-module changes.
BASE_CSS = (
    profile.root_css()
    + """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: var(--font-body);
    background: radial-gradient(1200px 600px at 70% -10%, var(--bg-glow) 0%, var(--bg) 55%) fixed;
    color: var(--text); min-height: 100vh; line-height: 1.5; -webkit-font-smoothing: antialiased;
  }
  h1, h2, h3, .bebas { font-family: var(--font-head); font-weight: 400; letter-spacing: 0.04em; }
  a { color: inherit; }
  header {
    display: flex; align-items: center; gap: 20px; padding: 18px 32px;
    border-bottom: 1px solid var(--line-soft); background: var(--bg-2);
    backdrop-filter: blur(6px); position: sticky; top: 0; z-index: 20;
  }
  .brand { font-size: 30px; letter-spacing: 0.12em; font-family: var(--font-head); }
  .brand b { color: var(--gold); }
  .who { font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--muted); }
"""
    + TOPNAV_CSS
    + """
  main { max-width: 940px; margin: 0 auto; padding: 32px; }
  .section-label { font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--gold); margin-bottom: 12px; font-weight: 600; }
  .btn {
    border: 1px solid var(--line); background: var(--btn-bg); color: var(--text);
    font-family: inherit; font-size: 13px; font-weight: 600; cursor: pointer;
    border-radius: 10px; padding: 9px 16px; transition: all 0.15s; letter-spacing: 0.02em;
  }
  .btn:hover { border-color: var(--gold-line); color: var(--gold); }
  .btn:disabled { opacity: 0.5; cursor: default; }
  .btn-gold { background: var(--gold); border-color: var(--gold); color: var(--on-gold); }
  .btn-gold:hover { background: var(--gold-hover); border-color: var(--gold-hover); color: var(--on-gold); }
  .btn-sm { padding: 6px 11px; font-size: 12px; }
  textarea, input[type=text], input[type=date], select {
    background: var(--field); border: 1px solid var(--line); border-radius: 9px;
    color: var(--text); font-family: inherit; font-size: 14px; padding: 10px 12px;
  }
  textarea:focus, input:focus, select:focus { outline: none; border-color: var(--gold-line); }
  .card { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 14px; padding: 22px; }
"""
)


# ── Footer (quick links + tour button) ────────────────────────────────────────
# Links default to this project's Jira / GitHub; override the Jira board URL
# with NEO_JIRA_BOARD_URL if your board id differs.
_JIRA_BASE = os.environ.get("NEO_JIRA_BASE_URL", "https://mariahdiharris.atlassian.net").rstrip("/")
_PROJECT = os.environ.get("NEO_JIRA_PROJECT", "NEO")
_REPO = os.environ.get("NEO_GITHUB_REPO", "mariahdi/neo")
_JIRA_BOARD = os.environ.get("NEO_JIRA_BOARD_URL") or f"{_JIRA_BASE}/jira/software/projects/{_PROJECT}/boards/67"


def footer() -> str:
    # Calm internal links everyone gets; developer links + the dev-flavored tour
    # only on instances that opt in (dev_links) — Neo/Aria, never a gentle
    # consumer instance like Nessa.
    links = ['<a href="/me">⚙ You</a>']
    if not ACTIVE.get("hide_data_export"):  # gentle instances (e.g. Nessa) skip the export/import rabbit hole
        links.append('<a href="/data">⬇ Your data</a>')
    links.append('<a href="/aria">✦ Your ARIA</a>')
    internal = "".join(links)
    dev_html = ""
    # The tour is for everyone (customers included); the dev links stay dev-only.
    tour_html = '<button class="footer-tour" onclick="neoTour()">★ Take a tour</button>'
    if ACTIVE.get("dev_links"):
        repo = f"https://github.com/{_REPO}"
        links = [
            (_JIRA_BOARD, "Jira board"),
            (repo, "GitHub"),
            (f"{repo}/pulls", "Open PRs"),
            (f"{repo}/blob/main/docs/SETUP.md", "Setup guide"),
            (f"{repo}/blob/main/docs/DEPLOY.md", "Deploy guide"),
        ]
        dev_html = "".join(
            f'<a href="{href}" target="_blank" rel="noopener">{label} ↗</a>' for href, label in links
        )
    return (
        '<footer class="footer"><div class="footer-inner">'
        f'<div class="footer-links">{internal}{dev_html}</div>'
        f"{tour_html}"
        "</div></footer>"
    )


# Footer + tour styles. Injected into the work-board page too (EXTRA_CSS) and
# appended to BASE_CSS for module pages.
EXTRA_CSS = """
  .footer { border-top: 1px solid var(--line-soft); margin-top: 44px; padding: 20px 32px; }
  .footer-inner { max-width: 1240px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
  .footer-links { display: flex; gap: 18px; flex-wrap: wrap; }
  .footer-links a { font-size: 12px; color: var(--muted); text-decoration: none; letter-spacing: 0.03em; }
  .footer-links a:hover { color: var(--gold); }
  .footer-tour { background: none; border: 1px solid var(--gold-line); color: var(--gold); font-family: inherit; font-size: 11.5px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; padding: 8px 16px; border-radius: 9px; cursor: pointer; }
  .footer-tour:hover { background: var(--gold-soft); }
  #tour-ov { position: fixed; inset: 0; z-index: 9999; pointer-events: none; }
  .tour-block { position: absolute; inset: 0; pointer-events: auto; }
  .tour-spot { position: absolute; border-radius: 10px; border: 2px solid var(--gold); box-shadow: 0 0 0 9999px rgba(6,9,18,0.74); transition: all 0.2s ease; pointer-events: none; }
  .tour-pop { position: absolute; max-width: 300px; background: var(--panel-2); border: 1px solid var(--gold-line); border-radius: 12px; padding: 16px; box-shadow: 0 14px 44px rgba(0,0,0,0.55); pointer-events: auto; }
  .tour-title { font-family: 'Bebas Neue', sans-serif; font-size: 21px; letter-spacing: 0.04em; color: var(--gold); margin-bottom: 6px; }
  .tour-body { font-size: 13px; line-height: 1.6; color: var(--text); margin-bottom: 14px; }
  .tour-foot { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
  .tour-prog { font-size: 11px; color: var(--muted); }
  .tour-btns { display: flex; gap: 7px; }
  .tour-b { background: none; border: 1px solid var(--line); color: var(--text); font-family: inherit; font-size: 12px; padding: 6px 12px; border-radius: 8px; cursor: pointer; }
  .tour-b:hover { border-color: var(--gold-line); color: var(--gold); }
  .tour-b.gold { background: var(--gold); border-color: var(--gold); color: #1a1305; }
"""

# Interactive cross-page tour. Self-contained; exposes window.neoTour().
TOUR_JS = r"""
(function(){
  const STEPS = [
    {title:"Welcome to Aria", body:"Here's a quick 30-second tour of your space. Hit Next, or Skip any time."},
    {page:"/", sel:"#catalog", title:"Your dashboards", body:"Everything in Aria is a dashboard — health, finances, goals, career, and more. Tap any card to open it."},
    {page:"/", sel:"#catalog", title:"Turn on what you want", body:"Add or remove modules anytime. Aria only shows what you actually use — nothing extra, no noise."},
    {sel:".topnav", title:"Move around", body:"Jump between your active spaces up here. Your dashboard is always one click away."},
    {sel:".footer-links", title:"Yours to keep", body:"Down here live your settings, your own ARIA & themes, and your data — which you can export or delete anytime. No lock-in, ever."},
    {sel:".logout", title:"You're all set ✦", body:"You stay signed in between visits; sign out here whenever you like. That's the tour — enjoy Aria!"},
  ];
  const KEY = "neo_tour";
  let cur = 0, ro = null, onReflow = null;
  const esc = (s) => (s==null?"":String(s)).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

  function teardown(){
    const o=document.getElementById("tour-ov"); if(o) o.remove();
    document.removeEventListener("keydown", onKey);
    if(ro){ ro.disconnect(); ro=null; }
    if(onReflow){ window.removeEventListener("scroll", onReflow, true); window.removeEventListener("resize", onReflow); onReflow=null; }
  }
  function end(){ sessionStorage.removeItem(KEY); teardown(); }

  function go(i){
    if(i>=STEPS.length){ end(); return; }
    if(i<0) i=0;
    cur=i; sessionStorage.setItem(KEY, String(i));
    const step=STEPS[i];
    if(step.page && step.page!==location.pathname){ location.href = step.page + "?tour=" + i; return; }
    waitFor(step, i, 0);
  }
  function waitFor(step, i, tries){
    if(step.sel && !document.querySelector(step.sel) && tries<20){ setTimeout(()=>waitFor(step,i,tries+1), 150); return; }
    render(step, step.sel ? document.querySelector(step.sel) : null, i);
  }
  function render(step, el, i){
    teardown();
    const ov=document.createElement("div"); ov.id="tour-ov";
    ov.innerHTML = '<div class="tour-block"></div><div class="tour-spot"></div><div class="tour-pop"></div>';
    document.body.appendChild(ov);
    const spot=ov.querySelector(".tour-spot"), pop=ov.querySelector(".tour-pop");
    pop.innerHTML = '<div class="tour-title">'+esc(step.title)+'</div>'
      + '<div class="tour-body">'+esc(step.body)+'</div>'
      + '<div class="tour-foot"><span class="tour-prog">'+(i+1)+' / '+STEPS.length+'</span>'
      + '<span class="tour-btns">'
      + (i>0?'<button class="tour-b" data-a="back">Back</button>':'')
      + '<button class="tour-b" data-a="skip">Skip</button>'
      + '<button class="tour-b gold" data-a="next">'+(i===STEPS.length-1?'Done':'Next')+'</button>'
      + '</span></div>';
    pop.querySelectorAll(".tour-b").forEach(b => b.addEventListener("click", () => {
      const a=b.dataset.a; if(a==="next") go(cur+1); else if(a==="back") go(cur-1); else end();
    }));
    if(el){
      el.scrollIntoView({behavior:"smooth", block:"center"});
      const reflow = () => place(spot, pop, el);
      setTimeout(reflow, 320);
      // Re-measure when the target grows (cards/data load async) or on scroll/resize,
      // so the spotlight wraps the real element, not an empty container.
      onReflow = reflow;
      window.addEventListener("scroll", reflow, true);
      window.addEventListener("resize", reflow);
      if(window.ResizeObserver){ ro = new ResizeObserver(reflow); ro.observe(el); }
      else { setTimeout(reflow, 900); }
    } else {
      spot.style.display="none";
      pop.style.left="50%"; pop.style.top="42%"; pop.style.transform="translate(-50%,-50%)";
    }
    document.addEventListener("keydown", onKey);
  }
  function place(spot, pop, el){
    const r=el.getBoundingClientRect(), pad=8;
    spot.style.display="block";
    spot.style.left=(r.left-pad)+"px"; spot.style.top=(r.top-pad)+"px";
    spot.style.width=(r.width+pad*2)+"px"; spot.style.height=(r.height+pad*2)+"px";
    const ph=pop.offsetHeight, pw=pop.offsetWidth, vw=innerWidth, vh=innerHeight;
    let top=r.bottom+12; if(top+ph>vh-12) top=Math.max(12, r.top-ph-12);
    let left=Math.min(Math.max(12, r.left), vw-pw-12);
    pop.style.left=left+"px"; pop.style.top=top+"px"; pop.style.transform="none";
  }
  function onKey(e){ if(e.key==="Escape") end(); else if(e.key==="ArrowRight") go(cur+1); else if(e.key==="ArrowLeft") go(cur-1); }

  function resume(){
    const u=new URLSearchParams(location.search);
    const q=u.get("tour");
    if(sessionStorage.getItem(KEY)===null) return;          // tour not active
    if(q!==null){ u.delete("tour"); history.replaceState({}, "", location.pathname + (u.toString()?("?"+u):"")); }
    const i = q!==null ? parseInt(q,10) : parseInt(sessionStorage.getItem(KEY),10);
    go(isNaN(i)?0:i);
  }

  window.neoTour = function(){
    // Starting the tour (auto or manual) marks it seen, so it never auto-starts again.
    try { fetch("/api/tour/seen", {method:"POST"}); } catch(e){}
    sessionStorage.setItem(KEY,"0"); go(0);
  };
  function init(){
    resume();  // continue an in-progress tour (e.g. across a page nav)
    // Auto-start once for a brand-new account: server says it hasn't been seen,
    // nothing's already running, and we're on the dashboard.
    if(sessionStorage.getItem(KEY)===null && window.NEO_TOUR_AUTOSTART && location.pathname==="/"){
      window.neoTour();
    }
  }
  if(document.readyState==="loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
"""


def tour_tag() -> str:
    """The per-user auto-start flag + the tour script, for the page shell.

    The flag is resolved server-side from the store so the tour fires exactly
    once for a fresh account. Falls back to no-autostart if there's no user
    context (e.g. a page rendered outside a request)."""
    try:
        # Demo instances always offer the tour (every visitor gets the walkthrough);
        # normal accounts autostart it exactly once, until dismissed.
        if profile.ACTIVE.get("demo"):
            autostart = True
        else:
            autostart = not (store.load("tour", {}) or {}).get("seen")
    except Exception:
        autostart = False
    return (f"<script>window.NEO_TOUR_AUTOSTART={'true' if autostart else 'false'};</script>"
            f"<script>{TOUR_JS}</script>")


BASE_CSS = BASE_CSS + EXTRA_CSS


# Loads every font any profile might use (Bebas Neue, Inter, DM Mono); Georgia
# is a system serif. The active profile's font-* tokens pick which apply.
FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@400;500&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
)


def pwa_head() -> str:
    """PWA install tags + service-worker registration, injected into every page."""
    bg = ACTIVE.get("tokens", {}).get("bg", "#0f1115")
    return (
        '<link rel="manifest" href="/manifest.webmanifest">'
        f'<meta name="theme-color" content="{bg}">'
        '<link rel="apple-touch-icon" href="/static/icon-192.png">'
        "<script>if('serviceWorker' in navigator){navigator.serviceWorker.register('/sw.js').catch(function(){})}</script>"
    )


def embed(body: str) -> str:
    """A chrome-free render of a module body — no nav / footer / tour — for
    embedding one dashboard inside another (e.g. the Finance & Wealth zoom canvas)."""
    ov = themes.override_css()
    ov_tag = f"<style>{ov}</style>" if ov else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{FONT_LINK}
<style>{BASE_CSS}</style>
{ov_tag}
<style>body{{padding:18px 20px;background:var(--bg);}} .cat-tabs{{display:none!important;}} main{{margin:0!important;}}</style>
</head>
<body>
{body}
</body>
</html>"""


def page(title: str, body: str, active: str = "") -> str:
    """Wrap a page `body` in the full shared HTML shell (nav + footer + tour)."""
    ov = themes.override_css()  # per-user theme choice wins over the profile default
    ov_tag = f"<style>{ov}</style>" if ov else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — {ACTIVE["name"]}</title>
{FONT_LINK}
{pwa_head()}
<style>{BASE_CSS}</style>
{ov_tag}
</head>
<body>
{nav(active)}
{body}
{footer()}
{tour_tag()}
</body>
</html>"""
