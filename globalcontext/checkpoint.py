"""Checkpoint / recover logic for reliable Global Context updates.

A checkpoint is a small JSON marker written next to `.globalcontext.md` before
an AI starts a response. When the response finishes and the summary is written,
the marker is removed. If the session crashes, the marker persists on disk and
the next session can recover it.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .context import append_entry
from .lock import LockError, locked
from .utils import find_context_file, get_context_path, globalcontext_home, now_str


PENDING_SUFFIX = ".pending"
RECOVERY_LABEL = "Recovery"
RECOVERY_STALE_SECONDS = 300  # 5 minutes


def _pending_path(context_path: Path) -> Path:
    """Return the pending-marker path for a context file."""
    return Path(str(context_path) + PENDING_SUFFIX)


def _marker_info(marker: Path) -> dict[str, Any] | None:
    """Read and return pending marker JSON, or None if invalid/missing."""
    if not marker.exists():
        return None
    try:
        return json.loads(marker.read_text(encoding="utf-8"))
    except Exception:
        return None


def _is_process_alive(pid: int | None) -> bool:
    """Return True if the given PID is alive."""
    if pid is None or pid <= 0:
        return False
    try:
        if os.name == "nt":
            import ctypes  # noqa: PLC0415

            kernel = ctypes.windll.kernel32
            handle = kernel.OpenProcess(1, False, pid)
            if not handle:
                return False
            kernel.CloseHandle(handle)
            return True
        else:
            os.kill(pid, 0)
            return True
    except (OSError, ProcessLookupError):
        return False


def _is_stale(marker: Path, info: dict[str, Any] | None = None) -> bool:
    """Return True if the marker is stale (old or owner dead)."""
    if info is None:
        info = _marker_info(marker)
    if info is None:
        return True
    pid = info.get("pid")
    started = info.get("started_at")
    if not _is_process_alive(pid):
        return True
    if started:
        try:
            started_dt = datetime.fromisoformat(started)
            age = (datetime.now(timezone.utc) - started_dt).total_seconds()
            return age > RECOVERY_STALE_SECONDS
        except Exception:
            return True
    return False


def checkpoint(context_path: Path | None = None, ai: str = "AI", summary: str = "") -> Path:
    """Write a pending-update marker before an AI response.

    Returns the path to the marker file.
    """
    path = (context_path or get_context_path(create=True)).resolve()
    marker = _pending_path(path)

    with locked(path, timeout=10.0):
        data = {
            "context_file": str(path),
            "ai": ai,
            "pid": os.getpid(),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
        }
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return marker


def checkpoint_complete(
    context_path: Path | None = None,
    ai: str = "AI",
    text: str = "",
    clear_only: bool = False,
) -> Path:
    """Append the summary entry and remove the pending marker.

    If `text` is provided, it is appended as a new entry. If `clear_only` is
    True, only the marker is removed (useful when the AI already wrote the
    entry itself).
    """
    path = (context_path or get_context_path(create=True)).resolve()
    marker = _pending_path(path)

    with locked(path, timeout=10.0):
        if text and not clear_only:
            append_entry(text, label=ai, cwd=path.parent)
        if marker.exists():
            marker.unlink()

    return path


def recover(context_path: Path | None = None, dry_run: bool = False) -> list[Path]:
    """Scan for and consolidate stale pending markers.

    If `context_path` is given, only check that file's marker. Otherwise scan
    the GC home directory and registered project directories for markers.

    Returns a list of recovered marker paths.
    """
    recovered: list[Path] = []

    if context_path is not None:
        candidates = [(Path(context_path).resolve(), Path(str(context_path) + PENDING_SUFFIX))]
    else:
        candidates = _find_all_markers()

    for ctx_path, marker in candidates:
        info = _marker_info(marker)
        if info is None:
            # Marker is unreadable; remove it.
            if not dry_run:
                try:
                    marker.unlink()
                except FileNotFoundError:
                    pass
            recovered.append(marker)
            continue

        if not _is_stale(marker, info):
            continue

        if not dry_run:
            with locked(ctx_path, timeout=10.0):
                # Re-check after acquiring lock.
                if not marker.exists():
                    continue
                info = _marker_info(marker)
                if info is None or not _is_stale(marker, info):
                    continue

                ai = info.get("ai", RECOVERY_LABEL)
                started = info.get("started_at", "unknown")
                summary = info.get("summary", "")
                recovery_text = (
                    f"- Session with **{ai}** started at `{started}` was interrupted "
                    f"before the context could be updated.\n"
                )
                if summary:
                    recovery_text += f"- Last known intent: {summary}\n"
                recovery_text += (
                    "- Please review recent changes and update this log with a concise entry."
                )
                append_entry(recovery_text, label=RECOVERY_LABEL, cwd=ctx_path.parent)
                marker.unlink()

        recovered.append(marker)

    return recovered


def _find_all_markers() -> list[tuple[Path, Path]]:
    """Return (context_path, marker_path) tuples for all discovered markers."""
    results: list[tuple[Path, Path]] = []
    seen: set[Path] = set()

    # GC home directory.
    gc_home = globalcontext_home()
    if gc_home.exists():
        for marker in gc_home.rglob(f"*{PENDING_SUFFIX}"):
            ctx_path = Path(str(marker)[: -len(PENDING_SUFFIX)])
            if ctx_path not in seen:
                results.append((ctx_path, marker))
                seen.add(ctx_path)

    # Registered projects.
    try:
        from .registry import list_projects  # noqa: PLC0415

        for project_path in list_projects().values():
            ctx_path = Path(project_path).resolve() / ".globalcontext.md"
            marker = _pending_path(ctx_path)
            if marker.exists() and ctx_path not in seen:
                results.append((ctx_path, marker))
                seen.add(ctx_path)
    except Exception:
        pass

    # Current directory.
    current = find_context_file()
    if current is not None:
        marker = _pending_path(current)
        if marker.exists() and current not in seen:
            results.append((current, marker))

    return results


def has_pending(context_path: Path | None = None) -> bool:
    """Return True if there is a pending marker for the given/current context."""
    if context_path is not None:
        return _pending_path(Path(context_path).resolve()).exists()
    current = find_context_file()
    if current is None:
        return False
    return _pending_path(current).exists()


__all__ = [
    "checkpoint",
    "checkpoint_complete",
    "recover",
    "has_pending",
    "LockError",
]
