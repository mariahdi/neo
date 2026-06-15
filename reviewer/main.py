"""
Neo Web App — dashboard (control panel) + reviewer screens.
Wired to real Jira data via review_api / dashboard_api; actions via actions_api.
"""

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from .review_api import get_review_queue, get_proposal, DEMO_MODE
from .actions_api import approve as do_approve, request_changes as do_request_changes
from .dashboard_api import get_dashboard, create_request

app = FastAPI(title="Neo", version="0.2.0")

# ── Shared CSS ────────────────────────────────────────────────────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Inter', sans-serif; background: #1a1a1a; color: #f0ece4; min-height: 100vh; }
nav { background: #111; padding: 16px 32px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2a2a2a; }
nav a { color: #f0ece4; text-decoration: none; font-weight: 900; font-size: 15px; letter-spacing: 0.05em; text-transform: uppercase; }
nav a span { color: #e85d26; }
.nav-user { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 0.1em; }
main { max-width: 860px; margin: 40px auto; padding: 0 32px; }
h1 { font-size: 28px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 6px; }
h1 span { color: #e85d26; }
.subtitle { font-size: 13px; color: #888; margin-bottom: 32px; }
.card { background: #242424; border: 1px solid #333; border-radius: 8px; padding: 18px 20px; margin-bottom: 12px; display: flex; align-items: center; gap: 14px; transition: border-color 0.15s; }
.card:hover { border-color: #e85d26; }
.card-info { flex: 1; }
.card-title { font-size: 14px; font-weight: 700; color: #f0ece4; }
.card-meta { font-size: 12px; color: #888; margin-top: 5px; }
.tag { border-radius: 20px; padding: 3px 10px; font-size: 10px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }
.tag-hot { background: #e85d26; color: white; }
.tag-std { background: #2e2e2e; border: 1px solid #444; color: #aaa; }
.btn { border: 1.5px solid #444; border-radius: 6px; padding: 8px 18px; font-size: 12px; font-family: 'Inter', sans-serif; font-weight: 600; cursor: pointer; background: transparent; color: #f0ece4; text-decoration: none; display: inline-block; letter-spacing: 0.03em; transition: all 0.15s; }
.btn:hover { border-color: #e85d26; color: #e85d26; }
.btn-primary { background: #e85d26; border-color: #e85d26; color: white; }
.btn-primary:hover { background: #d14e1a; border-color: #d14e1a; color: white; }
.btn-lavender { background: #b8a9d9; border-color: #b8a9d9; color: #1a1a1a; }
.btn-lavender:hover { background: #a898c8; border-color: #a898c8; }
.back { font-size: 12px; color: #888; text-decoration: none; display: block; margin-bottom: 20px; letter-spacing: 0.03em; }
.back:hover { color: #e85d26; }
.proposal-header { border-bottom: 1px solid #333; padding-bottom: 16px; margin-bottom: 20px; }
.proposal-header h2 { font-size: 20px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.02em; }
.proposal-header .meta { font-size: 12px; color: #888; margin-top: 6px; }
.draft { background: #1e1e1e; border: 1px solid #333; border-radius: 8px; padding: 20px; font-size: 13px; line-height: 1.8; margin-bottom: 24px; color: #ccc; }
.draft h3 { font-size: 10px; color: #e85d26; text-transform: uppercase; letter-spacing: 0.12em; font-weight: 700; margin-bottom: 14px; }
.action-bar { display: flex; gap: 10px; border-top: 1px solid #333; padding-top: 20px; }
textarea { width: 100%; min-height: 140px; border: 1.5px solid #333; border-radius: 8px; padding: 14px; font-size: 13px; font-family: 'Inter', sans-serif; margin: 14px 0; resize: vertical; background: #1e1e1e; color: #f0ece4; }
textarea:focus { outline: none; border-color: #e85d26; }
textarea::placeholder { color: #555; }
.context-bar { background: #1e1e1e; border: 1px dashed #333; border-radius: 6px; padding: 10px 14px; font-size: 12px; color: #888; margin-bottom: 20px; }
.context-bar strong { color: #f0ece4; }
.confirm-box { background: #242424; border: 1px solid #333; border-radius: 12px; padding: 48px 32px; text-align: center; }
.checkmark { width: 64px; height: 64px; background: #e85d26; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 28px; margin: 0 auto 20px; color: white; }
.confirm-box h2 { font-size: 24px; font-weight: 900; text-transform: uppercase; margin-bottom: 10px; }
.confirm-box p { font-size: 13px; color: #aaa; margin-bottom: 8px; line-height: 1.6; }
.confirm-box .note { font-size: 12px; color: #666; font-style: italic; margin-bottom: 28px; }
hr { border: none; border-top: 1px solid #333; margin: 24px 0; }
.section-label { font-size: 10px; color: #e85d26; text-transform: uppercase; letter-spacing: 0.12em; font-weight: 700; margin-bottom: 8px; }
.nav-links { display: flex; gap: 22px; }
.nav-links a { font-size: 12px; font-weight: 600; letter-spacing: 0.06em; color: #888; text-transform: uppercase; }
.nav-links a:hover, .nav-links a.active { color: #e85d26; }
main.wide { max-width: 1180px; }
.dash-head { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 28px; gap: 20px; flex-wrap: wrap; }
.board { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; align-items: start; }
@media (max-width: 900px) { .board { grid-template-columns: repeat(2, 1fr); } }
.col { background: #1e1e1e; border: 1px solid #2a2a2a; border-radius: 10px; padding: 14px; }
.col-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.col-head h3 { font-size: 12px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.08em; }
.col-count { font-size: 11px; font-weight: 700; color: #1a1a1a; background: #e85d26; border-radius: 20px; padding: 1px 9px; }
.col-blurb { font-size: 11px; color: #666; margin-bottom: 12px; line-height: 1.4; }
.mini { display: block; background: #242424; border: 1px solid #333; border-radius: 7px; padding: 11px 12px; margin-bottom: 9px; text-decoration: none; color: #f0ece4; transition: border-color 0.15s; }
a.mini:hover { border-color: #e85d26; }
.mini-title { font-size: 12.5px; font-weight: 700; line-height: 1.35; }
.mini-meta { font-size: 11px; color: #888; margin-top: 6px; display: flex; align-items: center; gap: 8px; }
.dot-hot { width: 7px; height: 7px; border-radius: 50%; background: #e85d26; display: inline-block; }
.col-empty { font-size: 11px; color: #555; font-style: italic; padding: 6px 2px; }
.demo-banner { background: #2a2418; border-bottom: 1px solid #4a3f1e; color: #e8c66a; font-size: 12px; letter-spacing: 0.04em; text-align: center; padding: 8px 16px; }
.demo-banner strong { color: #f2b01e; }
"""

# Shown under the nav when no credentials are configured.
DEMO_BANNER = (
    '<div class="demo-banner"><strong>DEMO MODE</strong> · showing sample data — '
    'set the Jira / GitHub / Anthropic keys to go live.</div>'
) if DEMO_MODE else ""

def nav(active: str = ""):
    def cls(name):
        return ' class="active"' if name == active else ""
    return (
        '<nav>'
        '<a href="/"><span>Neo</span></a>'
        '<div class="nav-links">'
        f'<a href="/"{cls("dashboard")}>Dashboard</a>'
        f'<a href="/reviews"{cls("reviews")}>Reviews</a>'
        '</div>'
        '<span class="nav-user">Mariah</span>'
        '</nav>'
    ) + DEMO_BANNER

# ── Screen 1: My Reviews (live from Jira) ────────────────────────────────────
@app.get("/reviews", response_class=HTMLResponse)
async def list_reviews():
    proposals = get_review_queue()
    rows = ""
    for p in proposals:
        tag = f'<span class="tag tag-hot">HOT</span>' if p.get("category") == "HOT" else f'<span class="tag tag-std">STD</span>'
        amount = p.get("amount") or "—"
        deadline = f'Due {p["deadline"]}' if p.get("deadline") else ""
        sender = p.get("sender") or "—"
        rows += f"""
        <div class="card">
          <div class="card-info">
            <div class="card-title">{p["title"]}</div>
            <div class="card-meta">From: {sender} &nbsp;·&nbsp; {amount} &nbsp;·&nbsp; {deadline}</div>
          </div>
          {tag}
          <a href="/reviews/{p["id"]}" class="btn">Open →</a>
        </div>"""

    if not rows:
        rows = '<p style="color:#666;text-align:center;padding:40px 0;">No proposals in review right now.</p>'

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>My Reviews — Neo</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap" rel="stylesheet">
    <style>{CSS}</style></head><body>
    {nav("reviews")}
    <main>
      <h1>My <span>Reviews</span></h1>
      <p class="subtitle">{len(proposals)} proposal{"s" if len(proposals) != 1 else ""} waiting for your sign-off.</p>
      {rows}
    </main></body></html>"""

# ── Screen 2: Proposal View ───────────────────────────────────────────────────
@app.get("/reviews/{proposal_id}", response_class=HTMLResponse)
async def view_proposal(proposal_id: str):
    p = get_proposal(proposal_id)
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    draft_html = "".join(f"<p style='margin-bottom:10px;'>{line}</p>" for line in p["draft"].strip().split("\n\n"))
    tag = f'<span class="tag tag-hot">HOT</span>' if p["category"] == "HOT" else f'<span class="tag tag-std">STD</span>'

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>{p["title"]} — Neo</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap" rel="stylesheet">
    <style>{CSS}</style></head><body>
    {nav()}
    <main>
      <a href="/reviews" class="back">← Back to My Reviews</a>
      <div class="proposal-header">
        <h2>{p["title"]} &nbsp;{tag}</h2>
        <div class="meta">{p["amount"]} &nbsp;·&nbsp; {p["sender"]} &nbsp;·&nbsp; Due {p["deadline"]}</div>
      </div>
      <div class="draft">
        <h3>Claude's Draft</h3>
        {draft_html}
      </div>
      <div class="action-bar">
        <form method="POST" action="/reviews/{proposal_id}/approve">
          <button type="submit" class="btn btn-primary">✓ Approve</button>
        </form>
        <a href="/reviews/{proposal_id}/comment" class="btn">✎ Request Changes</a>
        <a href="/reviews/{proposal_id}/comment?mode=reprompt" class="btn btn-lavender">↺ Re-prompt</a>
      </div>
    </main></body></html>"""

# ── Screen 3: Comment / Request Changes ──────────────────────────────────────
@app.get("/reviews/{proposal_id}/comment", response_class=HTMLResponse)
async def comment_form(proposal_id: str, mode: str = "changes"):
    p = get_proposal(proposal_id)
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    title = "Re-prompt Claude" if mode == "reprompt" else "Request Changes"
    sub = "Give Claude new context and it will regenerate the proposal." if mode == "reprompt" else "Claude will see this feedback and revise the proposal."

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>{title} — Neo</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap" rel="stylesheet">
    <style>{CSS}</style></head><body>
    {nav()}
    <main>
      <a href="/reviews/{proposal_id}" class="back">← Back to Proposal</a>
      <div class="context-bar">Reviewing: <strong>{p["title"]}</strong></div>
      <h1>{title}</h1>
      <p class="subtitle">{sub}</p>
      <form method="POST" action="/reviews/{proposal_id}/comment">
        <input type="hidden" name="mode" value="{mode}">
        <textarea name="feedback" placeholder='e.g. "The budget breakdown is missing. Add a section showing how the funds are split across year 1 and year 2."'></textarea>
        <div style="display:flex;gap:10px;justify-content:flex-end;">
          <a href="/reviews/{proposal_id}" class="btn">Cancel</a>
          <button type="submit" class="btn btn-primary">Send to Claude →</button>
        </div>
      </form>
    </main></body></html>"""

@app.post("/reviews/{proposal_id}/comment", response_class=HTMLResponse)
async def submit_comment(proposal_id: str, feedback: str = Form(...), mode: str = Form("changes")):
    result = do_request_changes(proposal_id, feedback, mode)
    print(f"[NEO-13] Request changes {proposal_id} (mode={mode}): {result}")
    return RedirectResponse(url=f"/reviews/{proposal_id}/confirmed?action=changes", status_code=303)

# ── Screen 4: Approve ─────────────────────────────────────────────────────────
@app.post("/reviews/{proposal_id}/approve", response_class=HTMLResponse)
async def approve(proposal_id: str):
    result = do_approve(proposal_id)
    print(f"[NEO-13] Approve {proposal_id}: {result}")
    return RedirectResponse(url=f"/reviews/{proposal_id}/confirmed?action=approved", status_code=303)

# ── Screen 4: Confirmation ────────────────────────────────────────────────────
@app.get("/reviews/{proposal_id}/confirmed", response_class=HTMLResponse)
async def confirmed(proposal_id: str, action: str = "approved"):
    p = get_proposal(proposal_id)
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if action == "approved":
        icon, heading, message, note = (
            "✓",
            "Approved!",
            f"The {p['title']} proposal has been approved and is parked for final sign-off.",
            "Once the owner approves, the ticket moves to Done and the PR merges automatically."
        )
    else:
        icon, heading, message, note = (
            "✎",
            "Feedback sent!",
            f"Your feedback on {p['title']} has been sent to Claude.",
            "Claude will revise the proposal and it will return to your queue when ready."
        )

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>{heading} — Neo</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap" rel="stylesheet">
    <style>{CSS}</style></head><body>
    {nav()}
    <main>
      <div class="confirm-box">
        <div class="checkmark">{icon}</div>
        <h2>{heading}</h2>
        <p>{message}</p>
        <p class="note">{note}</p>
        <hr>
        <p style="font-weight:bold;margin-bottom:16px;">Great work. Ready for the next one?</p>
        <a href="/reviews" class="btn btn-primary">← Back to My Reviews</a>
      </div>
    </main></body></html>"""

# ── Dashboard: central control panel ─────────────────────────────────────────
def _fmt_date(iso: str | None) -> str:
    """ISO date (2026-09-15) -> 'Sep 15, 2026'; pass through anything odd."""
    if not iso:
        return ""
    try:
        y, m, d = (int(x) for x in iso.split("-")[:3])
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return f"{months[m - 1]} {d}, {y}"
    except Exception:
        return iso


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    data = get_dashboard()
    cols_html = ""
    for col in data["columns"]:
        cards = ""
        for it in col["items"]:
            clickable = col["key"] == "review"
            hot = '<span class="dot-hot"></span>HOT' if it["category"] == "HOT" else ""
            due = f'Due {_fmt_date(it["deadline"])}' if it["deadline"] else ""
            sep = " &nbsp;·&nbsp; " if hot and due else ""
            meta = f'<div class="mini-meta">{hot}{sep}{due}</div>' if (hot or due) else ""
            inner = f'<div class="mini-title">{it["title"]}</div>{meta}'
            if clickable:
                cards += f'<a class="mini" href="/reviews/{it["id"]}">{inner}</a>'
            else:
                cards += f'<div class="mini">{inner}</div>'
        if not cards:
            cards = '<div class="col-empty">Nothing here yet.</div>'
        cols_html += f"""
        <div class="col">
          <div class="col-head"><h3>{col["label"]}</h3><span class="col-count">{col["count"]}</span></div>
          <div class="col-blurb">{col["blurb"]}</div>
          {cards}
        </div>"""

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Dashboard — Neo</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap" rel="stylesheet">
    <style>{CSS}</style></head><body>
    {nav("dashboard")}
    <main class="wide">
      <div class="dash-head">
        <div>
          <h1>Control <span>Panel</span></h1>
          <p class="subtitle">{data["total"]} proposal{"s" if data["total"] != 1 else ""} in flight, start to sign-off.</p>
        </div>
        <a href="/new" class="btn btn-primary">🎙 Start New Voice Request</a>
      </div>
      <div class="board">{cols_html}</div>
    </main></body></html>"""


# ── New proposal request ──────────────────────────────────────────────────────
@app.get("/new", response_class=HTMLResponse)
async def new_request_form():
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>New Request — Neo</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap" rel="stylesheet">
    <style>{CSS}</style></head><body>
    {nav()}
    <main>
      <a href="/" class="back">← Back to Dashboard</a>
      <h1>New <span>Request</span></h1>
      <p class="subtitle">Describe the proposal in your own words, or paste a transcript. Neo takes it from here — drafts it and sends it back for your review.</p>
      <form method="POST" action="/new">
        <textarea name="text" placeholder='e.g. "The American Red Cross reached out about a $2.5M disaster-relief grant, due September 15th. They want to fund mobile shelters across the Gulf Coast."'></textarea>
        <div style="display:flex;gap:10px;justify-content:flex-end;">
          <a href="/" class="btn">Cancel</a>
          <button type="submit" class="btn btn-primary">Send to Neo →</button>
        </div>
      </form>
    </main></body></html>"""


@app.post("/new")
async def submit_request(text: str = Form(...)):
    try:
        new_id = create_request(text)
    except ValueError:
        return RedirectResponse(url="/new", status_code=303)
    print(f"[dashboard] created new request {new_id}")
    return RedirectResponse(url="/new/sent", status_code=303)


@app.get("/new/sent", response_class=HTMLResponse)
async def request_sent():
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Request Sent — Neo</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap" rel="stylesheet">
    <style>{CSS}</style></head><body>
    {nav()}
    <main>
      <div class="confirm-box">
        <div class="checkmark">🎙</div>
        <h2>Request Received!</h2>
        <p>Neo has your request and will start drafting the proposal.</p>
        <p class="note">It'll appear under <strong>Drafting</strong>, then land in <strong>Needs Review</strong> when it's ready for you.</p>
        <hr>
        <a href="/" class="btn btn-primary">← Back to Dashboard</a>
      </div>
    </main></body></html>"""
