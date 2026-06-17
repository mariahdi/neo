"""Tiny key/value store for dashboard module data, with two backends.

Default — **JSON files** under dashboard/data/ (or NEO_DATA_DIR). On Render this
is ephemeral: it resets on every redeploy.

Durable, free — set **DATABASE_URL** to a Postgres connection string (e.g. a
free Supabase or Neon project) and the store keeps everything in one small
key/value table instead, so About/Stocks/Goals/Wins survive redeploys with no
paid disk. Same load()/save() interface, so the modules don't change. Setup is
in docs/DEPLOY.md.

The store never crashes the app on a storage hiccup: a failed read returns the
default, a failed write is logged and skipped.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DB_URL = os.environ.get("DATABASE_URL")
_DATA_DIR = Path(os.environ.get("NEO_DATA_DIR") or (Path(__file__).resolve().parent / "data"))
_TABLE = "neo_store"
_pg_ready = False


# ── File backend (default) ────────────────────────────────────────────────────
def _file_path(name: str) -> Path:
    return _DATA_DIR / f"{name}.json"


def _file_load(name: str, default: Any) -> Any:
    try:
        return json.loads(_file_path(name).read_text())
    except (FileNotFoundError, ValueError):
        return default


def _file_save(name: str, data: Any) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _file_path(name).write_text(json.dumps(data, indent=2))


# ── Postgres backend (when DATABASE_URL is set) ───────────────────────────────
def _connect():
    import psycopg  # imported lazily so the file backend needs no driver
    return psycopg.connect(DB_URL, connect_timeout=10)


def _pg_init() -> None:
    global _pg_ready
    if _pg_ready:
        return
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE TABLE IF NOT EXISTS {_TABLE} "
                "(name text PRIMARY KEY, data jsonb NOT NULL, "
                "updated_at timestamptz DEFAULT now())"
            )
        conn.commit()
    _pg_ready = True


def _pg_load(name: str, default: Any) -> Any:
    _pg_init()
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT data FROM {_TABLE} WHERE name = %s", (name,))
            row = cur.fetchone()
    return row[0] if row else default  # jsonb comes back already parsed


def _pg_save(name: str, data: Any) -> None:
    _pg_init()
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {_TABLE} (name, data) VALUES (%s, %s::jsonb) "
                "ON CONFLICT (name) DO UPDATE SET data = EXCLUDED.data, updated_at = now()",
                (name, json.dumps(data)),
            )
        conn.commit()


# ── Public interface ──────────────────────────────────────────────────────────
def load(name: str, default: Any) -> Any:
    """Return the stored value for `name`, or `default` if absent/unreadable."""
    if DB_URL:
        try:
            return _pg_load(name, default)
        except Exception as e:
            print(f"[store] Postgres load '{name}' failed ({e}); using default")
            return default
    return _file_load(name, default)


def save(name: str, data: Any) -> None:
    """Persist `data` for `name`. Never raises — a write failure is logged."""
    if DB_URL:
        try:
            _pg_save(name, data)
            return
        except Exception as e:
            print(f"[store] Postgres save '{name}' failed: {e}")
            return
    _file_save(name, data)
