"""Command-line interface for Global Context."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, DEFAULT_CONTEXT_NAME
from .checkpoint import checkpoint, checkpoint_complete, recover
from .context import append_entry, init_context, read_context
from .integrations.claude import ClaudeIntegration
from .integrations.codex import CodexIntegration
from .integrations.gemini import GeminiIntegration
from .integrations.kimi import KimiIntegration
from .registry import create_project, list_projects, register, resolve, unregister
from .utils import find_context_file, globalcontext_home, now_str


INTEGRATIONS = [ClaudeIntegration(), KimiIntegration(), CodexIntegration(), GeminiIntegration()]


def _gc_home() -> Path:
    # The install root is the directory that bundles this package together with
    # the `integrations/` tree. Derive it from the package location so the CLI
    # finds its integrations no matter where it was installed (not just the
    # default ~/.globalcontext). Fall back to the conventional home otherwise.
    root = Path(__file__).resolve().parent.parent
    if (root / "integrations").exists():
        return root
    return globalcontext_home()


def cmd_init(args):
    path = init_context(Path(args.dir) if args.dir else None, force=args.force)
    print(f"Global Context initialized: {path}")


def cmd_status(args):
    path = find_context_file()
    if path:
        print(f"Active context: {path}")
        if args.show:
            print(read_context())
    else:
        print("No active context found.")
        print("Run: globalcontext init")


def cmd_append(args):
    source = Path(args.source)
    if not source.exists():
        print(f"Source file not found: {source}", file=sys.stderr)
        sys.exit(1)
    text = source.read_text(encoding="utf-8")
    path = append_entry(text, label=args.label)
    print(f"Appended to {path}")


def cmd_checkpoint(args):
    ctx = Path(args.context) if args.context else None
    marker = checkpoint(ctx, ai=args.ai, summary=args.summary or "", if_exists=args.if_exists)
    if marker is None:
        return  # no-op: --if-exists and no context file
    print(f"Checkpoint created: {marker}")


def cmd_checkpoint_complete(args):
    ctx = Path(args.context) if args.context else None
    path = checkpoint_complete(
        ctx,
        ai=args.ai,
        text=args.text or "",
        clear_only=args.clear_only,
        if_exists=args.if_exists,
    )
    if path is None:
        return  # no-op: --if-exists and no context file
    if args.clear_only or not args.text:
        print(f"Checkpoint cleared: {path}")
    else:
        print(f"Checkpoint complete: {path}")


def cmd_recover(args):
    ctx = Path(args.context) if args.context else None
    recovered = recover(ctx, dry_run=args.dry_run)
    if not recovered:
        print("No stale pending checkpoints found.")
        return
    action = "Would recover" if args.dry_run else "Recovered"
    print(f"{action} {len(recovered)} checkpoint(s):")
    for marker in recovered:
        print(f"  {marker}")


def cmd_sync(args):
    """Manual sync placeholder. In the future this can parse current AI session files."""
    print("Manual sync: use 'globalcontext append <file> --label <AI>'.")


def cmd_session_start(args):
    """Emit SessionStart hook JSON for Claude Code (cross-platform, no bash).

    Loads/creates the context file, recovers stale checkpoints, and prints a
    JSON object with `hookSpecificOutput.additionalContext` so Claude Code
    injects the shared context at session start. Never raises: on any error it
    prints an empty JSON object so the session is not disrupted.
    """
    import json

    try:
        if args.context:
            context_file = Path(args.context)
            if not context_file.exists():
                # Prefer legacy name if present in the same directory.
                legacy = context_file.parent / ".ai-shared-context.md"
                if legacy.exists():
                    context_file = legacy
        else:
            context_file = find_context_file() or (Path.cwd() / DEFAULT_CONTEXT_NAME)

        if not context_file.exists():
            if not args.create:
                # Global hook in a project without Global Context: stay inert.
                print("{}")
                return
            context_file.parent.mkdir(parents=True, exist_ok=True)
            from .utils import _default_header
            context_file.write_text(_default_header(context_file.parent), encoding="utf-8")

        # Consolidate any stale pending checkpoints before loading.
        try:
            recover(context_file)
        except Exception:
            pass

        content = context_file.read_text(encoding="utf-8")
        additional = (
            "## Global Context\n\n"
            "This project shares context across terminal AI assistants via "
            f"`{context_file.name}`.\n\n"
            "Current shared context:\n\n"
            f"{content}\n\n"
            "---\n\n"
            "Instructions for this session:\n"
            f"1. Read and remember the shared context above (file: `{context_file}`).\n"
            "2. If the user names another project (e.g. 'open project X'), run "
            "`globalcontext resolve <name-or-path>` and use that file instead.\n"
            "3. After significant changes, append ONE concise entry prefixed `Claude:` "
            "(3-8 bullets: what changed, key files, how to run/test, pending blockers). "
            "It is a hand-off log, not a transcript.\n"
            "4. Do not delete old entries unless asked."
        )
        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": additional,
            }
        }
        print(json.dumps(output))
    except Exception:
        # Never break the session on a hook error.
        print("{}")


def cmd_register(args):
    path = register(args.name, args.path)
    print(f"Registered '{args.name}' -> {Path(args.path).resolve()}")
    print(f"Registry saved to: {path}")


def cmd_unregister(args):
    if unregister(args.name):
        print(f"Unregistered '{args.name}'")
    else:
        print(f"Project '{args.name}' was not registered")


def cmd_list(args):
    projects = list_projects()
    if not projects:
        print("No registered projects.")
        print("Use: globalcontext register <name> <path>")
        return
    print("Registered projects:")
    for name, project_path in projects.items():
        print(f"  {name:<20} -> {project_path}")


def cmd_resolve(args):
    context_file = resolve(args.project)
    print(context_file)


def cmd_new(args):
    context_file = create_project(args.name, args.dir)
    print(f"Created project '{args.name}': {context_file.parent}")
    print(f"Context file: {context_file}")


def cmd_install(args):
    gc_home = _gc_home()
    selected = args.ai or []
    if not selected:
        selected = _interactive_select()
    if "all" in selected:
        selected = [i.name for i in INTEGRATIONS]

    results = []
    for name in selected:
        integration = next((i for i in INTEGRATIONS if i.name == name), None)
        if not integration:
            print(f"Unknown integration: {name}", file=sys.stderr)
            continue
        result = integration.install(gc_home)
        status = "OK" if result.success else "FAIL"
        print(f"[{status}] {integration.display_name}: {result.message}")
        results.append((integration.display_name, result.success))

    # Ensure global context exists in home
    home_ctx = Path.home() / DEFAULT_CONTEXT_NAME
    if not home_ctx.exists() and not (Path.home() / ".ai-shared-context.md").exists():
        home_ctx.write_text(_default_global_header(), encoding="utf-8")
        print(f"Created global context: {home_ctx}")

    if not results:
        print("No integrations selected; nothing installed.", file=sys.stderr)
        sys.exit(1)

    if all(r[1] for r in results):
        print("\nGlobal Context installed for selected AIs.")
    else:
        sys.exit(1)


def cmd_uninstall(args):
    selected = args.ai or []
    if not selected:
        selected = _interactive_select()
    if "all" in selected:
        selected = [i.name for i in INTEGRATIONS]

    for name in selected:
        integration = next((i for i in INTEGRATIONS if i.name == name), None)
        if not integration:
            print(f"Unknown integration: {name}", file=sys.stderr)
            continue
        result = integration.uninstall()
        status = "OK" if result.success else "FAIL"
        print(f"[{status}] {integration.display_name}: {result.message}")


def cmd_doctor(args):
    print(f"Global Context {__version__}")
    print(f"GC home: {_gc_home()}")
    print(f"Active context: {find_context_file() or 'none'}")
    print("\nAI integrations:")
    for i in INTEGRATIONS:
        detected = i.is_detected()
        installed = _is_integration_installed(i)
        print(f"  {i.display_name}: detected={detected}, installed={installed}")


def _is_integration_installed(integration) -> bool:
    if isinstance(integration, ClaudeIntegration):
        settings = Path.home() / ".claude" / "settings.json"
        if not settings.exists():
            return False
        try:
            return "globalcontext" in settings.read_text(encoding="utf-8")
        except OSError:
            return False
    if isinstance(integration, KimiIntegration):
        return (Path.home() / ".kimi-code" / "skills" / "globalcontext").exists()
    if isinstance(integration, CodexIntegration):
        return (Path.home() / ".codex" / "skills" / "globalcontext").exists()
    if isinstance(integration, GeminiIntegration):
        return (Path.home() / ".gemini" / "skills" / "globalcontext").exists()
    return False


def _interactive_select() -> list[str]:
    print("Select AI assistants to integrate (comma-separated numbers, or 'all'):")
    for idx, i in enumerate(INTEGRATIONS, 1):
        detected = "installed" if i.is_detected() else "not detected"
        print(f"  {idx}. {i.display_name} ({detected})")
    print("  a. all")
    choice = input("> ").strip()
    if choice.lower() == "a" or choice.lower() == "all":
        return ["all"]
    try:
        indices = [int(x.strip()) for x in choice.split(",")]
        return [INTEGRATIONS[idx - 1].name for idx in indices if 1 <= idx <= len(INTEGRATIONS)]
    except ValueError:
        return []


def _default_global_header() -> str:
    return f"""# Global Context

Shared context for terminal AI assistants (Claude Code, Kimi Code CLI, Codex, Gemini, etc.).

- **Location:** home directory
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


def main(argv=None):
    # Ensure UTF-8 output on Windows consoles that default to cp1252
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        prog="globalcontext",
        description="Share context across terminal AI coding assistants."
    )
    parser.add_argument("--version", action="version", version=f"globalcontext {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize a context file in the current directory")
    p_init.add_argument("--dir", help="Target directory (default: current)")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing context")

    p_status = sub.add_parser("status", help="Show active context file")
    p_status.add_argument("--show", action="store_true", help="Print context contents")

    p_append = sub.add_parser("append", help="Append a file's contents to the active context")
    p_append.add_argument("source", help="File to append")
    p_append.add_argument("--label", default="Session", help="Entry label, e.g. Kimi, Claude")

    p_checkpoint = sub.add_parser("checkpoint", help="Mark a pending context update before an AI response")
    p_checkpoint.add_argument("--context", help="Path to .globalcontext.md (default: active context)")
    p_checkpoint.add_argument("--ai", default="AI", help="AI assistant name, e.g. Claude, Kimi")
    p_checkpoint.add_argument("--summary", default="", help="Short summary of the planned update")
    p_checkpoint.add_argument("--if-exists", action="store_true", help="Do nothing if the context file does not exist")

    p_checkpoint_complete = sub.add_parser("checkpoint-complete", help="Append summary and clear the pending checkpoint")
    p_checkpoint_complete.add_argument("--context", help="Path to .globalcontext.md (default: active context)")
    p_checkpoint_complete.add_argument("--ai", default="AI", help="AI assistant name, e.g. Claude, Kimi")
    p_checkpoint_complete.add_argument("--text", default="", help="Summary text to append as a new entry")
    p_checkpoint_complete.add_argument("--clear-only", action="store_true", help="Only remove the pending marker")
    p_checkpoint_complete.add_argument("--if-exists", action="store_true", help="Do nothing if the context file does not exist")

    p_recover = sub.add_parser("recover", help="Consolidate stale pending checkpoints")
    p_recover.add_argument("--context", help="Path to .globalcontext.md (default: scan all known contexts)")
    p_recover.add_argument("--dry-run", action="store_true", help="Show what would be recovered without changing files")

    p_sync = sub.add_parser("sync", help="Manual sync helper")

    p_session_start = sub.add_parser("session-start", help="Emit SessionStart hook JSON for Claude Code")
    p_session_start.add_argument("--context", help="Path to .globalcontext.md (default: nearest)")
    p_session_start.add_argument("--create", action="store_true", help="Create the context file if missing (default: stay inert)")

    p_register = sub.add_parser("register", help="Register a project name to a directory")
    p_register.add_argument("name", help="Friendly project name")
    p_register.add_argument("path", help="Project directory path")

    p_unregister = sub.add_parser("unregister", help="Remove a registered project")
    p_unregister.add_argument("name", help="Project name")

    p_list = sub.add_parser("list", help="List registered projects")

    p_resolve = sub.add_parser("resolve", help="Resolve a project name/path to its context file")
    p_resolve.add_argument("project", help="Project name or path")

    p_new = sub.add_parser("new", help="Create a new project directory with Global Context")
    p_new.add_argument("name", help="Project name")
    p_new.add_argument("--dir", help="Optional custom directory (default: ~/GlobalContext-Projects/<name>)")

    p_install = sub.add_parser("install", help="Install AI integrations")
    p_install.add_argument("--ai", nargs="+", choices=[i.name for i in INTEGRATIONS] + ["all"],
                           help="AI assistants to install (default: interactive)")

    p_uninstall = sub.add_parser("uninstall", help="Uninstall AI integrations")
    p_uninstall.add_argument("--ai", nargs="+", choices=[i.name for i in INTEGRATIONS] + ["all"],
                             help="AI assistants to uninstall (default: interactive)")

    p_doctor = sub.add_parser("doctor", help="Check Global Context installation")

    args = parser.parse_args(argv)

    commands = {
        "init": cmd_init,
        "status": cmd_status,
        "append": cmd_append,
        "checkpoint": cmd_checkpoint,
        "checkpoint-complete": cmd_checkpoint_complete,
        "recover": cmd_recover,
        "sync": cmd_sync,
        "session-start": cmd_session_start,
        "register": cmd_register,
        "unregister": cmd_unregister,
        "list": cmd_list,
        "resolve": cmd_resolve,
        "new": cmd_new,
        "install": cmd_install,
        "uninstall": cmd_uninstall,
        "doctor": cmd_doctor,
    }
    commands[args.cmd](args)


if __name__ == "__main__":
    main()
