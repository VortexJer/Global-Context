"""Utility helpers for Global Context."""
import os
import platform
from pathlib import Path


def home() -> Path:
    """Return the user's home directory."""
    return Path.home()


def globalcontext_home() -> Path:
    """Return the Global Context installation directory."""
    return home() / ".globalcontext"


def now_str() -> str:
    """Return current UTC timestamp as a string."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def get_shell() -> str:
    """Detect the user's shell."""
    return os.environ.get("SHELL", "").split("/")[-1] or "unknown"


def is_windows() -> bool:
    return platform.system() == "Windows"


def find_context_file(cwd: Path | None = None) -> Path | None:
    """Find the nearest context file walking up from cwd."""
    cwd = cwd or Path.cwd()
    p = cwd.resolve()
    root = p.anchor
    while True:
        for name in (".globalcontext.md", ".ai-shared-context.md"):
            candidate = p / name
            if candidate.exists():
                return candidate
        if p == Path(root):
            break
        parent = p.parent
        if parent == p:
            break
        p = parent
    return None


def get_context_path(cwd: Path | None = None, create: bool = False) -> Path:
    """Return the context path for the current directory, optionally creating it."""
    cwd = cwd or Path.cwd()
    existing = find_context_file(cwd)
    if existing:
        return existing
    path = (cwd / ".globalcontext.md").resolve()
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(_default_header(cwd), encoding="utf-8")
    return path


def _default_header(cwd: Path) -> str:
    return f"""# Global Context

Shared context for terminal AI assistants (Claude Code, Kimi Code CLI, Codex, Gemini, etc.).

- **Project:** `{cwd}`
- **Created:** {now_str()}

## What this file is

This is a **project state log** (a hand-off journal), NOT a chat transcript. Each terminal AI assistant writes a short entry after a meaningful session so the next AI can continue without re-reading every file.

## Rules

- One entry per AI session when something important changed.
- Keep entries concise: 3–8 bullet points, no long prose.
- Start each entry with the AI name, e.g. **Claude:**, **Kimi:**, **Codex:**, **Gemini:**.
- Each entry must include:
  - What was done (created, modified, fixed, refactored).
  - Key files or directories touched.
  - How to run / test / use the current state.
  - Current status and any blockers or pending next steps.
- Do NOT paste conversation transcripts here.
- Do not delete old entries unless requested.
- If the file grows too large, add a `## Compacted Summary` section and archive older details.

---

"""
