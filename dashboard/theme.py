"""Shared look + page shell for the Neo dashboard's module pages.

The navy / gold / Bebas-Neue theme and the top navigation live here so About,
Stocks, Goals and Wins all feel like one app. The original work-board page in
main.py predates this and keeps its own inline CSS; it borrows nav(),
TOPNAV_CSS, footer(), EXTRA_CSS and TOUR_JS from here so the header, footer and
the interactive tour match everywhere.
"""
from __future__ import annotations

import os

from . import profile, registry

ACTIVE = profile.ACTIVE

# (key, href, label) — extended as each module ships.
NAV_LINKS = [
    ("dashboard", "/", "Dashboard"),
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
    for key, href, label in NAV_LINKS:
        if key != "dashboard" and key not in enabled:
            continue  # not enabled on this instance — hidden until opted in
        cls = ' class="active"' if key == active else ""
        links += f'<a href="{href}"{cls}>{label}</a>'
    new = registry.new_count()
    badge = f'<span class="nav-badge">{new}</span>' if new else ""
    mcls = ' class="active"' if active == "modules" else ""
    links += f'<a href="/modules"{mcls}>Modules{badge}</a>'
    return (
        "<header>"
        f'<a class="brand" href="/">{ACTIVE["wordmark"]}</a>'
        f'<nav class="topnav">{links}</nav>'
        f'<div class="who">{ACTIVE["who"]}</div>'
        f"{VIEW_BADGE}"
        f"{LOGOUT_BTN}"
        "</header>"
    )


# Audience view selector — cycles Private → Friends → Coworker → Public. Its
# label/color are set by VIEW_JS from the saved view; clicking cycles.
VIEW_BADGE = '<button class="view-badge" id="view-badge" title="Audience view — who can see this">🔒 Private ↻</button>'


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
  .nav-badge { display: inline-block; background: var(--gold); color: var(--on-gold); font-size: 9px; font-weight: 700; border-radius: 10px; padding: 0 5px; margin-left: 5px; vertical-align: 1px; }
  .logout { background: none; border: 1px solid var(--line); color: var(--muted); font-family: inherit; font-size: 10.5px; letter-spacing: 0.1em; text-transform: uppercase; cursor: pointer; border-radius: 8px; padding: 5px 11px; }
  .logout:hover { border-color: var(--gold-line); color: var(--gold); }
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
    border-bottom: 1px solid var(--line-soft); background: rgba(10,14,26,0.7);
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
    repo = f"https://github.com/{_REPO}"
    links = [
        (_JIRA_BOARD, "Jira board"),
        (repo, "GitHub"),
        (f"{repo}/pulls", "Open PRs"),
        (f"{repo}/blob/main/docs/SETUP.md", "Setup guide"),
        (f"{repo}/blob/main/docs/DEPLOY.md", "Deploy guide"),
    ]
    anchors = "".join(
        f'<a href="{href}" target="_blank" rel="noopener">{label} ↗</a>' for href, label in links
    )
    return (
        '<footer class="footer"><div class="footer-inner">'
        f'<div class="footer-links">{anchors}</div>'
        '<button class="footer-tour" onclick="neoTour()">★ Take a tour</button>'
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
  .view-badge { background: var(--vc, var(--gold-soft)); border: 1px solid var(--vc-line, var(--gold-line)); color: var(--vc-line, var(--gold)); font-family: inherit; font-size: 10px; letter-spacing: 0.05em; padding: 5px 12px; border-radius: 20px; cursor: pointer; white-space: nowrap; user-select: none; transition: all 0.15s; }
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
    {title:"Welcome to Neo", body:"A quick spin through what's here — your control room plus four modules. Use Next, or Skip any time."},
    {sel:"#chat-form", title:"Ask Neo", body:"Type (or speak) a request. Neo picks the right module, opens a Jira ticket, and starts the draft."},
    {sel:"#board .col:nth-child(1)", title:"1 · To Do", body:"Here's where a new request lands first — e.g. \"a proposal for the Red Cross.\""},
    {sel:"#board .col:nth-child(2)", title:"2 · In Progress", body:"Neo drafts it here, then opens a pull request behind the scenes."},
    {sel:"#board .col:nth-child(3)", title:"3 · In Review", body:"It shows up here as a card with the full draft and Approve / Request Changes / Re-prompt."},
    {sel:"#board .col:nth-child(4)", title:"4 · Done", body:"Approved and parked. That's the whole journey of one request — start to sign-off."},
    {sel:"#reviews", title:"Review inline", body:"Anything awaiting you appears here with its draft, so you approve or send it back without leaving the page."},
    {sel:"#widgets", title:"Modules at a glance", body:"Live counts across everything in flight."},
    {sel:".topnav", title:"Your modules", body:"Jump between Dashboard, Stocks, Goals, Wins and About up here — the tour visits each next."},
    {page:"/stocks", sel:"#view", title:"Stocks", body:"Your watchlist by sector. Hit Refresh on any card for a live AI briefing."},
    {page:"/stocks", sel:"#manage-btn", title:"Edit the watchlist", body:"Use Manage to add, swap, or remove sectors and stocks."},
    {page:"/goals", sel:".teller", title:"Goals — just say it", body:"Tell Neo \"weighed myself, 182\" and it logs progress to the right goal automatically."},
    {page:"/goals", sel:"#view", title:"Track progress", body:"Each goal shows a progress bar and a sparkline of its history."},
    {page:"/wins", sel:".teller", title:"Wins", body:"Describe your day; Neo spots the accomplishments and you confirm which ones to keep."},
    {page:"/wins", sel:"#list", title:"Your wins", body:"Grouped by day and tagged work / life / health / build."},
    {page:"/about", sel:".about-head", title:"About", body:"The story of how Neo was built — editable, with a shared photo and milestones."},
    {sel:".footer-links", title:"Quick links", body:"Your Jira board, GitHub, open PRs, and the setup/deploy guides all live down here."},
    {sel:".logout", title:"You're set", body:"You stay signed in between visits — sign out here whenever. That's the tour!"},
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

  window.neoTour = function(){ sessionStorage.setItem(KEY,"0"); go(0); };
  if(document.readyState==="loading") document.addEventListener("DOMContentLoaded", resume); else resume();
})();
"""

# Audience view-modes engine (NEO-38). A header badge cycles the view
# (Private → Friends → Coworker → Public); the choice persists in localStorage
# and sets data-view on <html>. Any module opts into masking by rendering a
# value as:  <span class="mask" data-real="3200" data-avg="2200" data-type="currency">…</span>
# and calling window.neoMaskScan() after it (re)renders. The engine then shows:
#   private  → the real value · friends/public → the average (or rounded) ·
#   coworker → "—" · public + currency → playful "monopoly money".
# Elements with data-views="private friends" are hidden in other views.
VIEW_JS = r"""
(function(){
  const VIEWS = ["private","friends","coworker","public"];
  const META = {
    private:  {label:"🔒 Private",  c:"rgba(208,176,240,0.16)", l:"#D0B0F0"},
    friends:  {label:"👥 Friends",  c:"rgba(128,212,160,0.16)", l:"#80D4A0"},
    coworker: {label:"💼 Coworker", c:"rgba(128,184,240,0.16)", l:"#80B8F0"},
    public:   {label:"🌍 Public",   c:"rgba(232,168,124,0.16)", l:"#E8A87C"},
  };
  const get = () => { const v = localStorage.getItem("neo-view"); return VIEWS.includes(v) ? v : "private"; };

  const fmtCur = (n) => "$" + Math.round(Number(n)||0).toLocaleString();
  const roundK = (n) => { n = Number(n)||0; return Math.abs(n) >= 1000 ? Math.round(n/1000)*1000 : Math.round(n/10)*10; };
  let seed = 42;
  function monopoly(n){
    seed = (seed*1664525 + 1013904223) & 0xffffffff;
    const mag = Math.max(1, Math.floor(Math.log10(Math.abs(Number(n))||1)));
    const fake = Math.round((3 + (Math.abs(seed)%7)) * Math.pow(10, mag-1)) * 10;
    const e = ["🐨","🎩","🚧","❤️","🔥","🐙","🦄","🍕"][Math.abs(seed)%8];
    return "$" + fake.toLocaleString() + " " + e;
  }
  function maskValue(real, avg, type, v){
    if(v === "private")  return type === "currency" ? fmtCur(real) : String(real);
    if(v === "coworker") return "—";
    if(v === "public" && type === "currency") return monopoly(real);
    const base = (avg !== undefined && avg !== "") ? avg : roundK(real);
    return type === "currency" ? fmtCur(base) : String(base);
  }

  function scan(v){
    v = v || get();
    document.querySelectorAll(".mask").forEach(el => {
      el.textContent = maskValue(el.dataset.real, el.dataset.avg, el.dataset.type || "text", v);
    });
    document.querySelectorAll("[data-views]").forEach(el => {
      el.style.display = el.getAttribute("data-views").split(/\s+/).includes(v) ? "" : "none";
    });
  }
  function apply(v){
    document.documentElement.setAttribute("data-view", v);
    const b = document.getElementById("view-badge");
    if(b){ b.textContent = META[v].label + " ↻"; b.style.setProperty("--vc", META[v].c); b.style.setProperty("--vc-line", META[v].l); }
    scan(v);
    window.dispatchEvent(new CustomEvent("neo:view", { detail: v }));
  }
  function set(v){ if(!VIEWS.includes(v)) return; localStorage.setItem("neo-view", v); apply(v); }
  function cycle(){ set(VIEWS[(VIEWS.indexOf(get()) + 1) % VIEWS.length]); }

  window.neoView = get;
  window.neoSetView = set;
  window.neoMaskScan = () => scan();   // modules call this after (re)rendering
  function init(){
    const b = document.getElementById("view-badge");
    if(b) b.addEventListener("click", cycle);
    apply(get());
  }
  if(document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
"""

BASE_CSS = BASE_CSS + EXTRA_CSS


# Loads every font any profile might use (Bebas Neue, Inter, DM Mono); Georgia
# is a system serif. The active profile's font-* tokens pick which apply.
FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@400;500&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
)


def page(title: str, body: str, active: str = "") -> str:
    """Wrap a page `body` in the full shared HTML shell (nav + footer + tour)."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — {ACTIVE["name"]}</title>
{FONT_LINK}
<style>{BASE_CSS}</style>
</head>
<body>
{nav(active)}
{body}
{footer()}
<script>{TOUR_JS}</script>
<script>{VIEW_JS}</script>
</body>
</html>"""
