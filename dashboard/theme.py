"""Shared look + page shell for the Neo dashboard's module pages.

The navy / gold / Bebas-Neue theme and the top navigation live here so About,
Stocks, Goals and Wins all feel like one app. The original work-board page in
main.py predates this and keeps its own inline CSS; it borrows nav() and
TOPNAV_CSS from here so the header matches everywhere.
"""
from __future__ import annotations

# (key, href, label) — extended as each module ships.
NAV_LINKS = [
    ("dashboard", "/", "Dashboard"),
    ("about", "/about", "About"),
]


def nav(active: str = "") -> str:
    """The shared top bar. `active` is the key of the current page."""
    links = ""
    for key, href, label in NAV_LINKS:
        cls = ' class="active"' if key == active else ""
        links += f'<a href="{href}"{cls}>{label}</a>'
    return (
        "<header>"
        '<a class="brand" href="/">NE<b>O</b></a>'
        f'<nav class="topnav">{links}</nav>'
        '<div class="who">Mariah &amp; Dad</div>'
        "</header>"
    )


# Just the nav pieces — injected into the legacy work-board page, which already
# styles header / .brand / .who itself.
TOPNAV_CSS = """
  .brand { text-decoration: none; }
  .topnav { display: flex; gap: 22px; margin-right: auto; margin-left: 10px; }
  .topnav a { font-size: 12px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); text-decoration: none; padding: 6px 0; }
  .topnav a:hover, .topnav a.active { color: var(--gold); }
"""

# Full shared stylesheet for new module pages.
BASE_CSS = (
    """
  :root {
    --bg: #0a0e1a; --bg-2: #0e1424; --panel: #121a2e; --panel-2: #16203a;
    --line: #243150; --line-soft: #1b2540; --text: #e9ecf4; --muted: #8794b3;
    --gold: #c8a84b; --gold-soft: rgba(200,168,75,0.14); --gold-line: rgba(200,168,75,0.45);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Inter', system-ui, sans-serif;
    background: radial-gradient(1200px 600px at 70% -10%, #15203a 0%, var(--bg) 55%) fixed;
    color: var(--text); min-height: 100vh; line-height: 1.5; -webkit-font-smoothing: antialiased;
  }
  h1, h2, h3, .bebas { font-family: 'Bebas Neue', 'Inter', sans-serif; font-weight: 400; letter-spacing: 0.04em; }
  a { color: inherit; }
  header {
    display: flex; align-items: center; gap: 20px; padding: 18px 32px;
    border-bottom: 1px solid var(--line-soft); background: rgba(10,14,26,0.7);
    backdrop-filter: blur(6px); position: sticky; top: 0; z-index: 20;
  }
  .brand { font-size: 30px; letter-spacing: 0.12em; font-family: 'Bebas Neue', sans-serif; }
  .brand b { color: var(--gold); }
  .who { font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--muted); }
"""
    + TOPNAV_CSS
    + """
  main { max-width: 940px; margin: 0 auto; padding: 32px; }
  .section-label { font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--gold); margin-bottom: 12px; font-weight: 600; }
  .btn {
    border: 1px solid var(--line); background: #0f1830; color: var(--text);
    font-family: inherit; font-size: 13px; font-weight: 600; cursor: pointer;
    border-radius: 10px; padding: 9px 16px; transition: all 0.15s; letter-spacing: 0.02em;
  }
  .btn:hover { border-color: var(--gold-line); color: var(--gold); }
  .btn:disabled { opacity: 0.5; cursor: default; }
  .btn-gold { background: var(--gold); border-color: var(--gold); color: #1a1305; }
  .btn-gold:hover { background: #d8b85a; border-color: #d8b85a; color: #1a1305; }
  .btn-sm { padding: 6px 11px; font-size: 12px; }
  textarea, input[type=text], input[type=date], select {
    background: #0c1322; border: 1px solid var(--line); border-radius: 9px;
    color: var(--text); font-family: inherit; font-size: 14px; padding: 10px 12px;
  }
  textarea:focus, input:focus, select:focus { outline: none; border-color: var(--gold-line); }
  .card { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 14px; padding: 22px; }
"""
)


def page(title: str, body: str, active: str = "") -> str:
    """Wrap a page `body` in the full shared HTML shell."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Neo</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{BASE_CSS}</style>
</head>
<body>
{nav(active)}
{body}
</body>
</html>"""
