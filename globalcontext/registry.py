"""Project registry for path-based Global Context lookup.

The registry maps friendly project names to project directories.
The actual context file always lives inside the project directory as
.globalcontext.md, so the context is tied to the project path.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .utils import globalcontext_home, now_str


def _registry_path() -> Path:
    return globalcontext_home() / "registry.json"


def _load_registry() -> dict:
    path = _registry_path()
    if not path.exists():
        return {"projects": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"projects": {}}


def _save_registry(registry: dict) -> None:
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")


def register(name: str, project_path: str | Path) -> Path:
    """Register a project name to a directory."""
    registry = _load_registry()
    registry["projects"][name] = str(Path(project_path).resolve())
    _save_registry(registry)
    return _registry_path()


def unregister(name: str) -> bool:
    """Remove a project from the registry."""
    registry = _load_registry()
    if name in registry["projects"]:
        del registry["projects"][name]
        _save_registry(registry)
        return True
    return False


def list_projects() -> dict[str, str]:
    """Return a dict of registered project names to paths."""
    return _load_registry()["projects"]


def resolve(name_or_path: str | Path) -> Path:
    """Resolve a project name or path to its context file.

    If name_or_path matches a registered project name, use that path.
    Otherwise treat it as a filesystem path.
    The context file at <project-path>/.globalcontext.md is created if missing.
    """
    key = str(name_or_path)
    registry = _load_registry()
    projects = registry.get("projects", {})

    if key in projects:
        project_dir = Path(projects[key])
    else:
        project_dir = Path(name_or_path).resolve()

    project_dir.mkdir(parents=True, exist_ok=True)
    context_file = project_dir / ".globalcontext.md"
    if not context_file.exists():
        from .utils import _default_header
        header = _default_header(project_dir)
        # Add a name line to the header
        header = header.replace(
            f"- **Project:** `{project_dir}`",
            f"- **Project:** `{project_dir}`\n- **Name:** `{key}`",
        )
        context_file.write_text(header, encoding="utf-8")
    return context_file


def resolve_path(name_or_path: str | Path) -> Path:
    """Resolve a project name or path to the project directory."""
    key = str(name_or_path)
    registry = _load_registry()
    projects = registry.get("projects", {})
    if key in projects:
        return Path(projects[key])
    return Path(name_or_path).resolve()


def default_projects_dir() -> Path:
    """Return the default directory for auto-created projects."""
    return Path.home() / "GlobalContext-Projects"


def create_project(name: str, project_dir: str | Path | None = None) -> Path:
    """Create a new project directory, register it, and create its context file.

    If project_dir is not provided, creates the project under the default
    GlobalContext-Projects directory. The folder name includes a path-derived
    suffix so projects with the same name at different locations do not collide
    and are easy to locate.
    """
    from .utils import _default_header

    if project_dir is None:
        base = default_projects_dir()
        # Use a temporary path to derive the suffix, then create the real folder.
        candidate = base / _sanitize(name)
        project_dir = base / _folder_name_for_project(name, candidate)
    else:
        project_dir = Path(project_dir).resolve()

    project_dir.mkdir(parents=True, exist_ok=True)
    context_file = project_dir / ".globalcontext.md"
    if not context_file.exists():
        header = _default_header(project_dir)
        # Add a name line to the header
        header = header.replace(
            f"- **Project:** `{project_dir}`",
            f"- **Project:** `{project_dir}`\n- **Name:** `{name}`",
        )
        context_file.write_text(header, encoding="utf-8")

    register(name, project_dir)
    return context_file


def _sanitize(name: str) -> str:
    """Sanitize a string for use as a directory name component."""
    import re
    safe = re.sub(r"[^\w\s-]", "", name, flags=re.UNICODE)
    safe = re.sub(r"[-\s]+", "-", safe).strip("-")
    return safe or "project"


def _folder_name_for_project(name: str, project_dir: Path) -> str:
    """Return a folder name that includes the project name and path info.

    Format: <name>--<drive>-<parent>
    Examples:
      C:\\StudyFlow          -> studyflow--c-studyflow
      C:\\Users\\foo\\Projects\\calc -> calc--c-projects
      ~/GlobalContext-Projects/calc -> calc--c-globalcontext-projects
    """
    resolved = project_dir.resolve()
    base = _sanitize(name)

    drive = resolved.drive.rstrip(":").lower() if resolved.drive else ""
    parent_name = _sanitize(resolved.parent.name) if resolved.parent.name else ""

    suffix_parts = [p for p in (drive, parent_name) if p]
    if not suffix_parts:
        return base

    # Avoid redundant name--c-name when parent equals name.
    if parent_name.lower() == base.lower() and len(suffix_parts) == 2:
        suffix_parts = [drive]

    suffix = "-".join(suffix_parts)
    return f"{base}--{suffix}"
