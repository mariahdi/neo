"""Tiny key/value store for dashboard module data, with two backends.

Default — **JSON files** under dashboard/data/ (or NEO_DATA_DIR). On Render this
is ephemeral: it resets on every redeploy.

Durable, free — set **DATABASE_URL** to a Postgres connection string (e.g. a
free Supabase or Neon project) and the store keeps everything in one small
key/value table instead, so About/Stocks/Goals/Wins survive redeploys with no
paid disk. Same load()/save() interface, so the modules don't change. Setup is
in docs/DEPLOY.md.

The store never crashes the app on a storage hiccup. When Postgres is the
backend it also mirrors every value to the local file as a last-known-good
cache, so a database that's down or paused doesn't look like data loss: a
failed read falls back to the cache (not an empty default), and a failed write
still lands in the cache (loudly logged) instead of being silently dropped.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DB_URL = os.environ.get("DATABASE_URL")
_DATA_DIR = Path(os.environ.get("NEO_DATA_DIR") or (Path(__file__).resolve().parent / "data"))
_TABLE = "neo_store"
# Each instance namespaces its Postgres rows so one database can serve many
# instances (default, nessa, …) without their data colliding. The file backend
# is already separated by NEO_DATA_DIR, so only the shared DB backend needs this.
_INSTANCE = (os.environ.get("NEO_PROFILE") or "neo").strip() or "neo"
_pg_ready = False


def _pg_name(name: str) -> str:
    return f"{_INSTANCE}:{name}"
_MISSING = object()  # distinguishes "no row / no cache" from a real default value


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
            cur.execute(f"SELECT data FROM {_TABLE} WHERE name = %s", (_pg_name(name),))
            row = cur.fetchone()
    return row[0] if row else default  # jsonb comes back already parsed


def _pg_save(name: str, data: Any) -> None:
    _pg_init()
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {_TABLE} (name, data) VALUES (%s, %s::jsonb) "
                "ON CONFLICT (name) DO UPDATE SET data = EXCLUDED.data, updated_at = now()",
                (_pg_name(name), json.dumps(data)),
            )
        conn.commit()


# ── Public interface ──────────────────────────────────────────────────────────
def load(name: str, default: Any) -> Any:
    """Return the stored value for `name`, or `default` if absent.

    With Postgres: read from the DB and mirror the result to the file cache. If
    the DB is unreachable, serve the last-known-good cache instead of silently
    returning empty — a paused/down database no longer looks like data loss.
    Without Postgres: read the file directly.
    """
    if not DB_URL:
        return _file_load(name, default)
    try:
        val = _pg_load(name, _MISSING)
    except Exception as e:
        cached = _file_load(name, _MISSING)
        if cached is not _MISSING:
            print(f"[store] Postgres load '{name}' failed ({e}); serving last-known-good file cache")
            return cached
        print(f"[store] Postgres load '{name}' failed ({e}); no cache yet, using default")
        return default
    if val is _MISSING:
        # Not in the DB — but a value may sit in the cache from a write made
        # while the DB was down. Prefer that over the bare default.
        return _file_load(name, default)
    try:
        _file_save(name, val)  # refresh the cache so it's ready for the next outage
    except Exception:
        pass
    return val


def save(name: str, data: Any) -> None:
    """Persist `data` for `name`. Never raises.

    With Postgres: write to the DB and mirror to the file cache. If the DB write
    fails, the data still lands in the cache (and is loudly logged) so the edit
    isn't silently lost within the session. Without Postgres: write the file.
    """
    if not DB_URL:
        _file_save(name, data)
        return
    try:
        _pg_save(name, data)
    except Exception as e:
        print(f"[store] Postgres save '{name}' FAILED ({e}); writing to file cache so the edit "
              "isn't lost — the database needs attention")
        try:
            _file_save(name, data)
        except Exception as e2:
            print(f"[store] file-cache save '{name}' also failed: {e2}")
        return
    try:
        _file_save(name, data)  # mirror the successful write into the cache
    except Exception:
        pass


def keys() -> list[str]:
    """All stored names, for whole-instance export. Backend-agnostic."""
    if not DB_URL:
        return sorted(p.stem for p in _DATA_DIR.glob("*.json")) if _DATA_DIR.exists() else []
    try:
        _pg_init()
        prefix = _INSTANCE + ":"
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT name FROM {_TABLE} WHERE name LIKE %s", (prefix + "%",))
                rows = cur.fetchall()
        return sorted(r[0][len(prefix):] for r in rows)
    except Exception as e:
        print(f"[store] keys() failed ({e}); using file cache")
        return sorted(p.stem for p in _DATA_DIR.glob("*.json")) if _DATA_DIR.exists() else []
