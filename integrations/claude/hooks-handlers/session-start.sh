#!/usr/bin/env bash
# Global Context — Claude Code SessionStart hook
# Auto-loads .globalcontext.md (or legacy .ai-shared-context.md) on session start.

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"

python3 - "$PROJECT_DIR" << 'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

project_dir = Path(sys.argv[1]).resolve()

# Prefer .globalcontext.md, fall back to legacy name
if (project_dir / ".globalcontext.md").exists():
    context_file = project_dir / ".globalcontext.md"
elif (project_dir / ".ai-shared-context.md").exists():
    context_file = project_dir / ".ai-shared-context.md"
else:
    context_file = project_dir / ".globalcontext.md"

# Create default context if none exists
if not context_file.exists():
    header = f"""# Global Context

Shared context for terminal AI assistants (Claude Code, Kimi Code CLI, Codex, Gemini, etc.).

- **Project:** `{project_dir}`
- **Created:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

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
    context_file.write_text(header, encoding="utf-8")

content = context_file.read_text(encoding="utf-8")

additional_context = (
    "## Global Context\\n\\n"
    "This project uses `.globalcontext.md` to share context across terminal AI assistants "
    "(Claude Code, Kimi Code CLI, Codex, etc.).\\n\\n"
    "Current shared context:\\n\\n"
    f"{content}\\n\\n"
    "---\\n\\n"
    "Instructions for this session:\\n"
    "1. Read and remember the shared context above.\\n"
    "2. If the user asks to continue work started in another AI, reference this file.\\n"
    "3. If the user mentions a project by name or path (e.g. 'open project graphify'), "
    "run `globalcontext resolve <name-or-path>` to find or create the correct `.globalcontext.md`. "
    "Use that resolved file instead of the current directory one.\\n"
    "4. If the user proposes a new project without a path (e.g. 'let's build a calculator'), "
    "automatically run `globalcontext new <project-name>` to create the project directory under "
    "`~/GlobalContext-Projects/`, register it, and create its `.globalcontext.md`.\\n"
    "5. You can register a project name with `globalcontext register <name> <path>`.\\n"
    "6. After making significant changes, append ONE concise project-state entry to the resolved `.globalcontext.md` using the prefix `Claude:`.\\n"
    "   This is a hand-off log, NOT a chat transcript. Use 3–8 bullets covering: what changed, key files touched, how to run/test the current state, and any pending blockers.\\n"
    "7. Do NOT paste conversation text into the context file.\\n"
    "8. Do not delete old entries unless the user asks."
)

output = {
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": additional_context,
    }
}

print(json.dumps(output))
PY

exit 0
