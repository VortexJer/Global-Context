"""Command-line interface for Global Context."""
import argparse
import sys
from pathlib import Path

from . import __version__, DEFAULT_CONTEXT_NAME
from .context import append_entry, init_context, read_context
from .integrations.claude import ClaudeIntegration
from .integrations.codex import CodexIntegration
from .integrations.gemini import GeminiIntegration
from .integrations.kimi import KimiIntegration
from .registry import create_project, list_projects, register, resolve, unregister
from .utils import find_context_file, globalcontext_home, now_str


INTEGRATIONS = [ClaudeIntegration(), KimiIntegration(), CodexIntegration(), GeminiIntegration()]


def _gc_home() -> Path:
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


def cmd_sync(args):
    """Manual sync placeholder. In the future this can parse current AI session files."""
    print("Manual sync: use 'globalcontext append <file> --label <AI>'.")


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
        return (Path.home() / ".claude" / "plugins" / "globalcontext").exists()
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

    p_sync = sub.add_parser("sync", help="Manual sync helper")

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
        "sync": cmd_sync,
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
