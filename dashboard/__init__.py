"""Neo unified dashboard — one FastAPI app for the whole flow.

Replaces the separate reviewer screens and the static dashboard. Reuses the
existing backend APIs unchanged:
    - reviewer.dashboard_api  — the live board (read)
    - reviewer.review_api     — In Review proposals + drafts (read)
    - reviewer.actions_api    — approve / request changes / re-prompt (write)
    - dashboard.chat          — the chat bar: request -> ticket -> draft
"""
