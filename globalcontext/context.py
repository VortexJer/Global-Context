"""Context file read/write operations."""
import re
from pathlib import Path
from typing import Iterable

from .lock import locked
from .utils import find_context_file, get_context_path, now_str


def read_context(cwd: Path | None = None) -> str:
    """Read the active context file, or return empty string if none exists."""
    path = find_context_file(cwd)
    if not path:
        return ""
    return path.read_text(encoding="utf-8")


def append_entry(text: str, label: str = "Session", cwd: Path | None = None) -> Path:
    """Append a new entry to the active context file."""
    path = get_context_path(cwd, create=True)
    entry = f"\n\n## {label} — {now_str()}\n\n{text.strip()}\n\n---\n"
    with locked(path, timeout=10.0):
        with open(path, "a", encoding="utf-8") as f:
            f.write(entry)
    return path


def init_context(cwd: Path | None = None, force: bool = False) -> Path:
    """Initialize a context file in the given directory."""
    cwd = (cwd or Path.cwd()).resolve()
    path = cwd / ".globalcontext.md"
    legacy = cwd / ".ai-shared-context.md"

    if path.exists() and not force:
        return path

    if legacy.exists() and not force:
        # Migrate legacy file to new name, preserving content
        path.parent.mkdir(parents=True, exist_ok=True)
        content = legacy.read_text(encoding="utf-8")
        path.write_text(content, encoding="utf-8")
        # Rename legacy to backup
        backup = cwd / ".ai-shared-context.md.backup"
        legacy.rename(backup)
        return path

    from .utils import _default_header
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_default_header(cwd), encoding="utf-8")
    return path


def list_entries(cwd: Path | None = None) -> Iterable[dict]:
    """Parse entries from the active context file."""
    content = read_context(cwd)
    # Split by level-2 headings
    parts = re.split(r"\n## ", content)
    for part in parts[1:]:
        lines = part.splitlines()
        if not lines:
            continue
        header = lines[0]
        body = "\n".join(lines[1:]).strip()
        yield {"header": header, "body": body}
