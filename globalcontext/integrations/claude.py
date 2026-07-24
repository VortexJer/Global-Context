"""Claude Code integration for Global Context.

Instead of a plugin (whose bash hook does not run on native Windows and which
must be enabled via a marketplace), this integration writes cross-platform
hooks directly into ``~/.claude/settings.json``:

- SessionStart      -> ``globalcontext session-start`` (injects shared context)
- UserPromptSubmit  -> ``globalcontext checkpoint --if-exists``
- Stop              -> ``globalcontext checkpoint-complete --clear-only --if-exists``

The hook command uses the ABSOLUTE path to the installed launcher so it does
not depend on PATH being refreshed in the shell that launched Claude.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from .base import Integration, IntegrationResult

HOOK_EVENTS = ("SessionStart", "UserPromptSubmit", "Stop")


def _settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def _legacy_plugin_dir() -> Path:
    return Path.home() / ".claude" / "plugins" / "globalcontext"


def _short_path(p: Path) -> str:
    """Return the Windows 8.3 short path (no spaces) for `p`, or str(p).

    Using a space-free launcher path is critical: Claude runs the hook via
    `cmd /c <command>`, and cmd strips the outer quotes when a command both
    starts and ends with a quote — turning a quoted `"C:\\Users\\Joaquin ERE\\..."`
    into the broken token `C:\\Users\\Joaquin`. A short path has no spaces, so it
    needs no quotes and survives that stripping.
    """
    s = str(p)
    if os.name != "nt":
        return s
    try:
        import ctypes
        from ctypes import wintypes

        fn = ctypes.windll.kernel32.GetShortPathNameW
        fn.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        fn.restype = wintypes.DWORD
        buf = ctypes.create_unicode_buffer(1024)
        if fn(s, buf, 1024) and buf.value:
            return buf.value
    except Exception:
        pass
    return s


def _launcher(gc_home: Path) -> str:
    """CLI launcher path for the current OS (short/space-free on Windows)."""
    if os.name == "nt":
        return _short_path(gc_home / "bin" / "globalcontext.cmd")
    return str(gc_home / "bin" / "globalcontext")


def _quote(launcher: str) -> str:
    """Quote the launcher only if it contains a space (short paths do not)."""
    return launcher if " " not in launcher else f'"{launcher}"'


def _gc_hooks(gc_home: Path, checkpoints: bool = False) -> dict:
    """Hooks to install.

    By default only `SessionStart` is installed — it loads the shared context
    once per session and is silent. The per-turn marker lifecycle
    (`UserPromptSubmit` + `Stop`) is opt-in via `checkpoints=True` because it
    runs the CLI on every prompt and every response, which most users find
    intrusive. Interrupted-turn recovery still runs at SessionStart.
    """
    launcher = _quote(_launcher(gc_home))
    ctx = '"${CLAUDE_PROJECT_DIR}/.globalcontext.md"'

    def cmd(rest: str) -> dict:
        return {"type": "command", "command": f"{launcher} {rest}"}

    hooks = {"SessionStart": [{"hooks": [cmd(f"session-start --context {ctx}")]}]}
    if checkpoints:
        hooks["UserPromptSubmit"] = [{"hooks": [cmd(f"checkpoint --context {ctx} --ai Claude --if-exists")]}]
        hooks["Stop"] = [{"hooks": [cmd(f"checkpoint-complete --context {ctx} --ai Claude --clear-only --if-exists")]}]
    return hooks


def _is_gc_command(entry: object) -> bool:
    return isinstance(entry, dict) and "globalcontext" in str(entry.get("command", ""))


def _strip_gc_hooks(settings: dict) -> bool:
    """Remove every Global Context hook from a settings dict. Returns True if
    anything was removed. Leaves all non-GC hooks untouched."""
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return False

    changed = False
    for event in list(hooks.keys()):
        groups = hooks.get(event)
        if not isinstance(groups, list):
            continue
        new_groups = []
        for group in groups:
            if not isinstance(group, dict):
                new_groups.append(group)
                continue
            inner = group.get("hooks")
            if isinstance(inner, list):
                kept = [h for h in inner if not _is_gc_command(h)]
                if len(kept) != len(inner):
                    changed = True
                if not kept:
                    continue  # whole group was ours -> drop it
                group = {**group, "hooks": kept}
            new_groups.append(group)
        if new_groups:
            hooks[event] = new_groups
        else:
            del hooks[event]
            changed = True

    if not hooks:
        settings.pop("hooks", None)
    return changed


def _read_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _write_settings(path: Path, settings: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


class ClaudeIntegration(Integration):
    name = "claude"
    display_name = "Claude Code"

    def is_detected(self) -> bool:
        return (Path.home() / ".claude").exists()

    def install(self, gc_home: Path) -> IntegrationResult:
        # Remove the old bash plugin if a previous version installed it.
        if _legacy_plugin_dir().exists():
            shutil.rmtree(_legacy_plugin_dir(), ignore_errors=True)

        path = _settings_path()
        settings = _read_settings(path)
        _strip_gc_hooks(settings)  # idempotent: clear any prior GC hooks first

        hooks = settings.setdefault("hooks", {})
        for event, groups in _gc_hooks(gc_home).items():
            hooks.setdefault(event, []).extend(groups)

        _write_settings(path, settings)
        return IntegrationResult(True, f"Configured Claude hooks in {path}")

    def uninstall(self) -> IntegrationResult:
        removed = []

        if _legacy_plugin_dir().exists():
            shutil.rmtree(_legacy_plugin_dir(), ignore_errors=True)
            removed.append("plugin dir")

        path = _settings_path()
        if path.exists():
            settings = _read_settings(path)
            if _strip_gc_hooks(settings):
                _write_settings(path, settings)
                removed.append("settings.json hooks")

        if removed:
            return IntegrationResult(True, f"Removed Claude integration ({', '.join(removed)})")
        return IntegrationResult(True, "Claude integration was not installed")
