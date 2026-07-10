---
name: globalcontext
description: Auto-load and update .globalcontext.md to share context across terminal AI assistants.
---

# Global Context

Global Context shares project context across terminal AI assistants (Claude Code, Kimi Code CLI, Codex, etc.).

Each project has a `.globalcontext.md` file inside its project directory. Projects can also be registered with a friendly name.

## What this file is

`.globalcontext.md` is a **project state log** (hand-off journal), NOT a chat transcript. After a meaningful session, write a short entry so the next AI can continue without re-reading every file.

## Finding or creating the context file

1. First, check whether `.globalcontext.md` exists in the current working directory.
2. If the user mentions a project by name (e.g. "open project graphify"), run:
   ```bash
   globalcontext resolve <project-name>
   ```
   This returns the path to the project's `.globalcontext.md`, creating it if needed.
3. If the user gives a project path directly, run:
   ```bash
   globalcontext resolve "<project-path>"
   ```
4. If the user proposes a **new project** without specifying a path (e.g. "let's build a calculator"), automatically create it:
   ```bash
   globalcontext new <project-name>
   ```
   This creates the project under `~/GlobalContext-Projects/<name>--<path>/` (the folder name includes the project name plus a path-derived suffix to avoid collisions and make it easy to find), registers it, and creates `.globalcontext.md`.
5. If no project is specified, fall back to the current directory.

## During the session

- Treat the resolved project directory as the working directory for that session.
- Read the `.globalcontext.md` and keep it in mind.
- At the start of the session, run `globalcontext recover` to consolidate any stale pending checkpoints.
- Before each assistant response, run `globalcontext checkpoint` against the resolved `.globalcontext.md` to create a pending marker.
- After completing a significant task or at session end, append **one concise project-state entry** to the resolved `.globalcontext.md` using the prefix `Codex:` and the current UTC date/time, then run `globalcontext checkpoint-complete --clear-only` to remove the pending marker.
- Each entry must be 3–8 bullet points covering: what changed, key files touched, how to run/test/use the current state, and any pending blockers.
- Do NOT paste conversation transcripts into the context file.
- Use available file tools to modify the file. Never corrupt it.

## Registering projects

If the user wants to name a project, run:
```bash
globalcontext register <name> "<project-path>"
```

## Entry format

```markdown
## Codex — 2026-07-10 14:30 UTC

- Created the `calculator/` package with `main.py` and `operations.py`.
- Implemented add/subtract/multiply/divide CLI commands.
- Run with: `python -m calculator.main 2 + 3`
- Tests pass: `pytest tests/`
- Pending: add power and sqrt operations.

---
```
