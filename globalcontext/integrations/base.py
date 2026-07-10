"""Base class for AI integrations."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import NamedTuple


class IntegrationResult(NamedTuple):
    success: bool
    message: str


class Integration(ABC):
    name: str = ""
    display_name: str = ""

    @abstractmethod
    def is_detected(self) -> bool:
        """Return True if the AI tool appears to be installed."""
        ...

    @abstractmethod
    def install(self, gc_home: Path) -> IntegrationResult:
        """Install the integration for this AI tool."""
        ...

    @abstractmethod
    def uninstall(self) -> IntegrationResult:
        """Remove the integration for this AI tool."""
        ...
