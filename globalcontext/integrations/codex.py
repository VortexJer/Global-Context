"""OpenAI Codex CLI integration for Global Context."""
import shutil
from pathlib import Path

from .base import Integration, IntegrationResult


class CodexIntegration(Integration):
    name = "codex"
    display_name = "OpenAI Codex CLI"

    def is_detected(self) -> bool:
        # Detect actual Codex CLI installation
        return (
            (Path.home() / ".codex" / "config.toml").exists()
            or (Path.home() / ".codex" / "packages").exists()
            or (Path.home() / ".codex" / "tmp").exists()
            or (Path.home() / ".codex" / "skills").exists()
        )

    def install(self, gc_home: Path) -> IntegrationResult:
        # Install Codex skill for auto-loading context
        src = gc_home / "integrations" / "codex" / "skills" / "globalcontext"
        dst = Path.home() / ".codex" / "skills" / "globalcontext"
        if dst.exists():
            shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst)

        # Also keep manual prompt template as reference
        prompt_dst = Path.home() / ".codex" / "globalcontext"
        prompt_dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(gc_home / "integrations" / "codex" / "prompt.md", prompt_dst / "prompt.md")

        return IntegrationResult(
            True,
            f"Installed Codex skill to {dst}\n"
            f"Manual prompt template saved to {prompt_dst / 'prompt.md'}"
        )

    def uninstall(self) -> IntegrationResult:
        dst = Path.home() / ".codex" / "skills" / "globalcontext"
        removed = []
        if dst.exists():
            shutil.rmtree(dst)
            removed.append(str(dst))
        prompt_dst = Path.home() / ".codex" / "globalcontext"
        if prompt_dst.exists():
            shutil.rmtree(prompt_dst)
            removed.append(str(prompt_dst))
        if removed:
            return IntegrationResult(True, f"Removed {', '.join(removed)}")
        return IntegrationResult(True, "Codex integration was not installed")
