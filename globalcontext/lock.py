"""Cross-platform file locking for Global Context.

Uses `filelock` when available (the standard robust solution for Windows,
Linux and macOS). Falls back to a simple lockfile protocol if `filelock` is
not installed.
"""
from __future__ import annotations

import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path

try:
    from filelock import FileLock, Timeout

    _HAS_FILELOCK = True
except Exception:  # pragma: no cover
    FileLock = None  # type: ignore[misc, assignment]
    Timeout = None  # type: ignore[misc, assignment]
    _HAS_FILELOCK = False


DEFAULT_TIMEOUT = 30.0
POLL_INTERVAL = 0.05
STALE_SECONDS = 60.0

# Reentrant lock tracking per thread, so nested `locked()` calls in the same
# process do not deadlock.
_lock_state = threading.local()


class LockError(Exception):
    """Raised when a lock cannot be acquired."""


def _held_locks() -> dict[str, int]:
    if not hasattr(_lock_state, "held"):
        _lock_state.held = {}
    return _lock_state.held


def _lock_path(path: Path) -> Path:
    return Path(str(path) + ".lock")


# ---------------------------------------------------------------------------
# filelock-based implementation
# ---------------------------------------------------------------------------


def _acquire_filelock(path: Path, timeout: float) -> None:
    lock_path = _lock_path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(lock_path), timeout=timeout)
    try:
        lock.acquire()
    except Timeout as exc:
        raise LockError(f"Could not acquire lock for {path} within {timeout}s") from exc
    return lock


# ---------------------------------------------------------------------------
# Fallback lockfile protocol
# ---------------------------------------------------------------------------


def _is_process_alive(pid: int) -> bool:
    """Return True if process with pid exists."""
    if pid <= 0:
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


def _read_lock(lock_path: Path) -> tuple[int, float] | None:
    """Read pid and timestamp from a lockfile."""
    try:
        text = lock_path.read_text(encoding="utf-8").strip()
        if not text:
            return None
        parts = text.split(":", 1)
        pid = int(parts[0])
        ts = float(parts[1]) if len(parts) > 1 else 0.0
        return pid, ts
    except Exception:
        return None


def _break_lock(lock_path: Path) -> None:
    """Remove a stale lockfile."""
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass


def _acquire_fallback(path: Path, timeout: float) -> None:
    """Acquire a lock using a lockfile protocol."""
    lock_path = _lock_path(path)
    deadline = time.time() + timeout

    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                data = f"{os.getpid()}:{time.time()}".encode("utf-8")
                os.write(fd, data)
            finally:
                os.close(fd)
            return
        except FileExistsError:
            info = _read_lock(lock_path)
            if info is not None:
                pid, ts = info
                now = time.time()
                if not _is_process_alive(pid) or now - ts > STALE_SECONDS:
                    _break_lock(lock_path)
                    continue

            if time.time() > deadline:
                raise LockError(
                    f"Could not acquire lock for {path} within {timeout}s "
                    f"(lock held by {info[0] if info else 'unknown'})"
                )
            time.sleep(POLL_INTERVAL)


def _release_fallback(path: Path) -> None:
    lock_path = _lock_path(path)
    info = _read_lock(lock_path)
    if info is None or info[0] == os.getpid():
        _break_lock(lock_path)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def acquire_lock(path: Path, timeout: float = DEFAULT_TIMEOUT):
    """Acquire a lock for `path`.

    Waits up to `timeout` seconds. Raises LockError on timeout.
    Reentrant within the same thread.
    """
    key = str(Path(path).resolve())
    held = _held_locks()

    if key in held:
        held[key] += 1
        return None

    if _HAS_FILELOCK:
        lock = _acquire_filelock(path, timeout)
        held[key] = 1
        return lock

    _acquire_fallback(path, timeout)
    held[key] = 1
    return None


def release_lock(path: Path, lock=None) -> None:
    """Release the lock for `path`."""
    key = str(Path(path).resolve())
    held = _held_locks()

    if key in held:
        held[key] -= 1
        if held[key] > 0:
            return
        del held[key]

    if _HAS_FILELOCK and lock is not None:
        try:
            lock.release()
        except Exception:
            pass
    else:
        _release_fallback(path)


@contextmanager
def locked(path: Path, timeout: float = DEFAULT_TIMEOUT):
    """Context manager that acquires and releases a file lock."""
    lock = acquire_lock(path, timeout=timeout)
    try:
        yield
    finally:
        release_lock(path, lock)
