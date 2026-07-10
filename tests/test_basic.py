"""Basic tests for Global Context."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from globalcontext.checkpoint import checkpoint, checkpoint_complete, recover
from globalcontext.context import append_entry, init_context, read_context
from globalcontext.lock import LockError, locked
from globalcontext.utils import find_context_file


def test_init_creates_context():
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        path = init_context(cwd)
        assert path.exists()
        assert path.name == ".globalcontext.md"
        text = path.read_text(encoding="utf-8")
        assert "Global Context" in text


def test_find_context_walks_up():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        child = root / "a" / "b"
        child.mkdir(parents=True)
        init_context(root)
        found = find_context_file(child)
        assert found is not None
        assert found.name == ".globalcontext.md"


def test_append_entry():
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        init_context(cwd)
        path = append_entry("Test summary", label="Kimi", cwd=cwd)
        text = path.read_text(encoding="utf-8")
        assert "## Kimi —" in text
        assert "Test summary" in text


def test_checkpoint_creates_pending_marker():
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        init_context(cwd)
        ctx = cwd / ".globalcontext.md"
        marker = checkpoint(ctx, ai="Claude", summary="planning")
        assert marker.exists()
        data = json.loads(marker.read_text(encoding="utf-8"))
        assert data["ai"] == "Claude"
        assert data["summary"] == "planning"
        assert Path(data["context_file"]).resolve() == ctx.resolve()


def test_checkpoint_complete_appends_and_removes_marker():
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        init_context(cwd)
        ctx = cwd / ".globalcontext.md"
        checkpoint(ctx, ai="Kimi", summary="work")
        checkpoint_complete(ctx, ai="Kimi", text="Done")
        assert not (cwd / ".globalcontext.md.pending").exists()
        text = ctx.read_text(encoding="utf-8")
        assert "## Kimi —" in text
        assert "Done" in text


def test_recover_consolidates_stale_marker():
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        init_context(cwd)
        ctx = cwd / ".globalcontext.md"
        marker = ctx.parent / (ctx.name + ".pending")
        data = {
            "context_file": str(ctx),
            "ai": "Codex",
            "pid": 99999,
            "started_at": "2026-01-01T00:00:00+00:00",
            "summary": "auth flow",
        }
        marker.write_text(json.dumps(data), encoding="utf-8")
        recovered = recover(ctx)
        assert recovered
        assert not marker.exists()
        text = ctx.read_text(encoding="utf-8")
        assert "## Recovery —" in text
        assert "auth flow" in text


def test_recover_skips_live_marker():
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        init_context(cwd)
        ctx = cwd / ".globalcontext.md"
        marker = ctx.parent / (ctx.name + ".pending")
        from datetime import datetime, timezone

        data = {
            "context_file": str(ctx),
            "ai": "Gemini",
            "pid": os.getpid(),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "summary": "current work",
        }
        marker.write_text(json.dumps(data), encoding="utf-8")
        recovered = recover(ctx)
        assert not recovered
        assert marker.exists()


def test_lock_is_reentrant():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ctx.md"
        path.write_text("x", encoding="utf-8")
        with locked(path, timeout=1.0):
            with locked(path, timeout=1.0):
                pass


def test_lock_blocks_other_process():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ctx.md"
        path.write_text("x", encoding="utf-8")
        script = f"""
import sys
import time
sys.path.insert(0, r'{Path(__file__).parent.parent}')
from globalcontext.lock import acquire_lock, release_lock
from pathlib import Path
p = Path(r'{path}')
lock = acquire_lock(p, timeout=0.5)
print('acquired')
sys.stdout.flush()
time.sleep(2)
release_lock(p, lock)
"""
        proc = subprocess.Popen(
            [sys.executable, "-c", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        # Wait for the child to acquire the lock.
        assert proc.stdout.readline().strip() == "acquired"

        try:
            with locked(path, timeout=0.5):
                pass
            raise AssertionError("Expected LockError")
        except LockError:
            pass
        finally:
            proc.wait(timeout=5)


def test_append_under_lock_no_corruption():
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        init_context(cwd)
        script = f"""
import sys
sys.path.insert(0, r'{Path(__file__).parent.parent}')
from globalcontext.context import append_entry
from pathlib import Path
append_entry('child', label='A', cwd=Path(r'{cwd}'))
"""
        procs = [
            subprocess.Popen([sys.executable, "-c", script])
            for _ in range(5)
        ]
        for p in procs:
            p.wait(timeout=10)
        text = (cwd / ".globalcontext.md").read_text(encoding="utf-8")
        assert text.count("## A —") == 5


if __name__ == "__main__":
    test_init_creates_context()
    test_find_context_walks_up()
    test_append_entry()
    test_checkpoint_creates_pending_marker()
    test_checkpoint_complete_appends_and_removes_marker()
    test_recover_consolidates_stale_marker()
    test_recover_skips_live_marker()
    test_lock_is_reentrant()
    test_lock_blocks_other_process()
    test_append_under_lock_no_corruption()
    print("All tests passed.")
