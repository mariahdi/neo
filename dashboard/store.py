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

import contextvars
import json
import os
import re
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
_MISSING = object()  # distinguishes "no row / no cache" from a real default value

# Per-user data isolation (NEO-93): a request-scoped current user, set by the
# auth middleware. Per-user keys get namespaced so users on one instance never
# see each other's data; SHARED keys stay instance-wide. No user set (local /
# unauthenticated) = instance-level, so existing single-user behavior is unchanged.
_user = contextvars.ContextVar("neo_user", default=None)
_SHARED = {"users", "aria_bank", "billing", "reset_tokens"}


def set_current_user(u) -> None:
    _user.set(u or None)


def current_user():
    """The current request's user id (or None) — for read-only checks like owner-ness."""
    return _user.get()


def _uslug(u: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", u)[:64]


def _scope(name: str) -> str:
    u = _user.get()
    return f"{_uslug(u)}::{name}" if (u and name not in _SHARED) else name


def _pg_name(name: str) -> str:
    return f"{_INSTANCE}:{_scope(name)}"


# Encryption-at-rest for personal data. Values for keys in ENCRYPTED_KEYS are
# stored as ciphertext when NEO_DATA_KEY (a Fernet key) is set, so a database/file
# peek reveals nothing. No key set = plaintext (graceful, e.g. local dev), and
# existing plaintext rows still read fine and re-encrypt on their next save.
#
# We encrypt all per-user personal content. We deliberately leave a few keys
# plaintext: operational state (theme, modules, tour, lock) that isn't personal,
# the public acronym bank (aria_bank), and the auth/billing shared keys (users,
# reset_tokens, billing) — so that LOGIN and BILLING never depend on the data key
# (losing/rotating NEO_DATA_KEY shouldn't lock everyone out or break Stripe).
ENCRYPTED_KEYS = {
    "wellness", "body",            # health & meds
    "nominal", "wealth",           # finances & investments
    "recipes", "goals", "wins",    # life content
    "trips", "career", "me",       # plans, job search, profile
    "about", "dailybread",         # story & faith
    "stocks", "aria_personal",     # watchlist & personal acronym
}
_FERNET = _MISSING


def _fernet():
    global _FERNET
    if _FERNET is _MISSING:
        key = os.environ.get("NEO_DATA_KEY")
        if not key:
            _FERNET = None
        else:
            try:
                from cryptography.fernet import Fernet
                _FERNET = Fernet(key.encode())
            except Exception as e:
                print(f"[store] encryption disabled — bad NEO_DATA_KEY ({e})")
                _FERNET = None
    return _FERNET


# ── File backend (default) ────────────────────────────────────────────────────
def _file_path(name: str) -> Path:
    u = _user.get()
    if u and name not in _SHARED:
        return _DATA_DIR / _uslug(u) / f"{name}.json"
    return _DATA_DIR / f"{name}.json"


def _file_load(name: str, default: Any) -> Any:
    try:
        return json.loads(_file_path(name).read_text())
    except (FileNotFoundError, ValueError):
        return default


def _file_save(name: str, data: Any) -> None:
    p = _file_path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))


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
    """Public read — transparently decrypts at-rest-encrypted values."""
    raw = _load_raw(name, default)
    if isinstance(raw, dict) and "__enc__" in raw:
        f = _fernet()
        if not f:
            print(f"[store] '{name}' is encrypted but NEO_DATA_KEY is unset; returning default")
            return default
        try:
            return json.loads(f.decrypt(raw["__enc__"].encode()).decode())
        except Exception as e:
            print(f"[store] decrypt '{name}' failed ({e}); returning default")
            return default
    return raw


def save(name: str, data: Any) -> None:
    """Public write — encrypts at-rest for ENCRYPTED_KEYS when a key is configured."""
    payload = data
    if name in ENCRYPTED_KEYS:
        f = _fernet()
        if f:
            payload = {"__enc__": f.encrypt(json.dumps(data).encode()).decode()}
    _save_raw(name, payload)


def _load_raw(name: str, default: Any) -> Any:
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


def _save_raw(name: str, data: Any) -> None:
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
    """The current user's stored names (for their data export) — per-user scoped,
    so an export only ever contains that user's own data. Backend-agnostic."""
    u = _user.get()

    def _from_files():
        d = (_DATA_DIR / _uslug(u)) if u else _DATA_DIR
        return sorted(p.stem for p in d.glob("*.json")) if d.exists() else []

    if not DB_URL:
        return _from_files()
    try:
        _pg_init()
        prefix = f"{_INSTANCE}:" + (f"{_uslug(u)}::" if u else "")
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT name FROM {_TABLE} WHERE name LIKE %s", (prefix + "%",))
                rows = cur.fetchall()
        out = []
        for (n,) in rows:
            rest = n[len(prefix):]
            if not u and "::" in rest:
                continue  # exclude other users' per-user rows when listing instance-level
            out.append(rest)
        return sorted(out)
    except Exception as e:
        print(f"[store] keys() failed ({e}); using file cache")
        return _from_files()


def health() -> dict:
    """Diagnostic snapshot of the storage backend — no secrets. Use to confirm
    on a live server whether Postgres is actually connected and holding data."""
    info = {
        "instance": _INSTANCE,
        "backend": "postgres" if DB_URL else "file",
        "db_url_configured": bool(DB_URL),
        "encryption_active": bool(_fernet()),
        "authed_user": bool(_user.get()),
    }
    if not DB_URL:
        info["note"] = ("No DATABASE_URL set — using file storage, which is "
                        "EPHEMERAL on Render (data is lost on restart/redeploy).")
        return info
    try:
        _pg_init()
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
                cur.execute(f"SELECT count(*) FROM {_TABLE} WHERE name LIKE %s", (f"{_INSTANCE}:%",))
                info["rows_for_instance"] = cur.fetchone()[0]
        info["postgres_ok"] = True
    except Exception as e:
        err = str(e).replace(DB_URL, "<DATABASE_URL>") if DB_URL else str(e)
        info["postgres_ok"] = False
        info["postgres_error"] = err[:300]
    return info


def migrate_user(from_user: str, to_user: str) -> list[str]:
    """One-time: copy a user's per-user data to another identity (e.g. an old
    env-login to an account email). Skips SHARED keys and anything the target
    already has, so it's safe to re-run. Returns the key names moved."""
    if not from_user or not to_user or from_user == to_user:
        return []
    prev = _user.get()
    moved: list[str] = []
    try:
        _user.set(from_user)
        names = [n for n in keys() if n not in _SHARED]
        data = {n: load(n, _MISSING) for n in names}
        _user.set(to_user)
        existing = set(keys())
        for n, v in data.items():
            if v is _MISSING or n in existing:
                continue
            save(n, v)
            moved.append(n)
    finally:
        _user.set(prev)
    return moved


def delete(name: str) -> None:
    """Delete a stored key for the current user/instance scope. Never raises."""
    try:
        p = _file_path(name)
        if p.exists():
            p.unlink()
    except Exception as e:
        print(f"[store] file delete '{name}' failed ({e})")
    if DB_URL:
        try:
            _pg_init()
            with _connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"DELETE FROM {_TABLE} WHERE name = %s", (_pg_name(name),))
                conn.commit()
        except Exception as e:
            print(f"[store] Postgres delete '{name}' failed ({e})")


def wipe_user() -> list[str]:
    """Delete ALL of the current user's per-user data. Shared keys (account,
    billing, community bank) are left intact. Returns the deleted key names."""
    names = [n for n in keys() if n not in _SHARED]
    for n in names:
        delete(n)
    return names
