"""Google Gemini CLI integration for Global Context."""
import shutil
from pathlib import Path

from .base import Integration, IntegrationResult


class GeminiIntegration(Integration):
    name = "gemini"
    display_name = "Google Gemini CLI"

    def is_detected(self) -> bool:
        return (Path.home() / ".gemini").exists()

    def install(self, gc_home: Path) -> IntegrationResult:
        src = gc_home / "integrations" / "gemini" / "skills" / "globalcontext"
        dst = Path.home() / ".gemini" / "skills" / "globalcontext"
        if dst.exists():
            shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst)
        return IntegrationResult(
            True,
            f"Installed Gemini skill to {dst}\n"
            "Run `gemini skills list --all` to verify, and if needed:\n"
            "  gemini skills enable globalcontext"
        )

    def uninstall(self) -> IntegrationResult:
        dst = Path.home() / ".gemini" / "skills" / "globalcontext"
        if dst.exists():
            shutil.rmtree(dst)
            return IntegrationResult(True, f"Removed {dst}")
        return IntegrationResult(True, "Gemini skill was not installed")
