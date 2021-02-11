"""The app module, containing the app factory function."""
import logging
from enum import Enum
from pathlib import Path
from subprocess import run

import rumps
from apscheduler.schedulers.background import BackgroundScheduler
from pluginbase import PluginBase
from rumps import MenuItem

from dontforget.constants import DEFAULT_PIPES_DIR_NAME, PROJECT_NAME
from dontforget.generic import UT
from dontforget.plugins.base import BasePlugin
from dontforget.settings import CONFIG_FILE_PATH, DEFAULT_DIRS, LOG_LEVEL, load_config_file

log_file = Path(DEFAULT_DIRS.user_log_dir) / "app.log"
log_file.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(filename=str(log_file))
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)


def load_plugins():
    """Load plugins."""
    plugin_base = PluginBase(package="dontforget.plugins")
    try:
        plugin_source = plugin_base.make_plugin_source(
            identifier=DEFAULT_PIPES_DIR_NAME,
            searchpath=[str(Path(__file__).parent / DEFAULT_PIPES_DIR_NAME)],
            persist=True,
        )
    except RuntimeError:
        # Ignore RuntimeError: This plugin source already exists
        return
    for plugin_module in plugin_source.list_plugins():
        plugin_source.load_plugin(plugin_module)


class DontForgetApp(rumps.App):
    """The macOS status bar application."""

    DEFAULT_TITLE = UT.ReminderRibbon

    class Menu(Enum):
        """Menu items."""

        Preferences = "Preferences..."
        ReloadConfigFile = "Reload config file"
        Quit = f"Quit {PROJECT_NAME}"

    def __init__(self):
        super(DontForgetApp, self).__init__(self.DEFAULT_TITLE, quit_button=self.Menu.Quit.value)

        logger.debug("Creating scheduler")
        self.scheduler = BackgroundScheduler()
        self.plugins: list = []

    def create_preferences_menu(self):
        """Create the preferences menu."""
        self.menu.add(MenuItem(self.Menu.Preferences.value, callback=self.clicked_preferences))
        self.menu.add(MenuItem(self.Menu.ReloadConfigFile.value, callback=self.clicked_reload_config_file))
        self.menu.add(rumps.separator)

    def clicked_preferences(self, _):
        """Open the config file on the preferred editor."""
        run(["open", str(CONFIG_FILE_PATH)])

    def clicked_reload_config_file(self, _):
        """Reload the config file and send it again to each loaded plugin."""
        config_yaml = load_config_file()
        for plugin in self.plugins:  # type: BasePlugin
            plugin.config_yaml = config_yaml
            plugin.reload_config()

    def start_scheduler(self) -> bool:
        """Start the scheduler."""
        logger.debug("Starting scheduler")
        self.scheduler.start()
        self.scheduler.print_jobs(out=log_file.open("a"))
        return True
