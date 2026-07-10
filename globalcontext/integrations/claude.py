"""Claude Code integration for Global Context."""
import shutil
from pathlib import Path

from .base import Integration, IntegrationResult


class ClaudeIntegration(Integration):
    name = "claude"
    display_name = "Claude Code"

    def is_detected(self) -> bool:
        return (Path.home() / ".claude").exists()

    def install(self, gc_home: Path) -> IntegrationResult:
        src = gc_home / "integrations" / "claude"
        dst = Path.home() / ".claude" / "plugins" / "globalcontext"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        return IntegrationResult(True, f"Installed Claude plugin to {dst}")

    def uninstall(self) -> IntegrationResult:
        dst = Path.home() / ".claude" / "plugins" / "globalcontext"
        if dst.exists():
            shutil.rmtree(dst)
            return IntegrationResult(True, f"Removed {dst}")
        return IntegrationResult(True, "Claude plugin was not installed")
