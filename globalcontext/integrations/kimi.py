"""Kimi Code CLI integration for Global Context."""
import shutil
from pathlib import Path

from .base import Integration, IntegrationResult


class KimiIntegration(Integration):
    name = "kimi"
    display_name = "Kimi Code CLI"

    def is_detected(self) -> bool:
        return (Path.home() / ".kimi-code").exists()

    def install(self, gc_home: Path) -> IntegrationResult:
        src = gc_home / "integrations" / "kimi"
        dst = Path.home() / ".kimi-code" / "skills" / "globalcontext"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        return IntegrationResult(True, f"Installed Kimi skill to {dst}")

    def uninstall(self) -> IntegrationResult:
        dst = Path.home() / ".kimi-code" / "skills" / "globalcontext"
        if dst.exists():
            shutil.rmtree(dst)
            return IntegrationResult(True, f"Removed {dst}")
        return IntegrationResult(True, "Kimi skill was not installed")
