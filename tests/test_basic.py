"""Basic tests for Global Context."""
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from globalcontext.context import append_entry, init_context, read_context
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


if __name__ == "__main__":
    test_init_creates_context()
    test_find_context_walks_up()
    test_append_entry()
    print("All tests passed.")
