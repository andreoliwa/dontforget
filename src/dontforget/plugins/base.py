"""Base plugin."""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from dontforget.app import DontForgetApp


class BasePlugin(ABC):
    """Base class for plugins."""

    app: "DontForgetApp"

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""
        return ""

    def __init__(self, config_yaml: Dict[str, Any]) -> None:
        self.config_yaml = config_yaml

    @property
    def plugin_config(self) -> List[Dict[str, Any]]:
        """Only the plugin configuration from the YAML file."""
        return self.config_yaml[self.name.lower()]

    @abstractmethod
    def init_app(self, app: "DontForgetApp") -> bool:
        """Init the plugin with application info."""
        pass

    @abstractmethod
    def reload_config(self) -> bool:
        """Actions to perform when the YAML config is reloaded."""
        pass
