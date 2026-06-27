"""Neo desktop launcher.

Runs the FastAPI app on a local port and shows it in a native window (pywebview),
so Neo feels like a real app — no browser, no terminal. Data lives in a per-user
folder so each person owns their own file.

  Run:                 python desktop.py
  Build (Windows .exe): see build-app.ps1
  Smoke test (no GUI):  set NEO_DESKTOP_CHECK=1 and run — boots the server,
                        confirms it answers, prints where data lives, then exits.
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import urllib.request


def _say(msg: str) -> None:
    try:
        print(msg)
    except Exception:
        pass  # --windowed builds have no stdout/stderr


def _data_dir() -> str:
    """A per-user folder the person owns — this is the 'own your data' file home."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "Neo")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/Neo")
    return os.path.expanduser("~/.neo")


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_until_up(port: int, timeout: float = 20.0) -> bool:
    url = f"http://127.0.0.1:{port}/api/billing/status"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


def main() -> int:
    os.environ.setdefault("NEO_PROFILE", "default")
    data_dir = _data_dir()
    os.makedirs(data_dir, exist_ok=True)
    os.environ.setdefault("NEO_DATA_DIR", data_dir)

    port = int(os.environ.get("NEO_DESKTOP_PORT") or _free_port())

    import uvicorn
    # In a --windowed build sys.stdout is None; uvicorn's default log formatter
    # calls sys.stdout.isatty() and crashes. Disable its logging config entirely.
    config = uvicorn.Config("dashboard.main:app", host="127.0.0.1", port=port,
                            log_config=None, access_log=False)
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()

    if not _wait_until_up(port):
        _say("Neo server failed to start")
        return 1

    url = f"http://127.0.0.1:{port}"

    # Headless self-test for CI / smoke testing — no native window.
    if os.environ.get("NEO_DESKTOP_CHECK"):
        _say(f"DESKTOP OK  ({url})  data: {data_dir}")
        server.should_exit = True
        return 0

    import webview
    webview.create_window("Neo", url, width=1180, height=820, min_size=(900, 600))
    webview.start()          # blocks until the window is closed
    server.should_exit = True
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
