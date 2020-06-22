"""The app module, containing the app factory function."""
import logging
import sys
from enum import Enum
from pathlib import Path
from subprocess import run

import click
import rumps
from appdirs import AppDirs
from apscheduler.schedulers.background import BackgroundScheduler
from pluginbase import PluginBase

from dontforget.constants import APP_NAME, CONFIG_YAML, DEFAULT_PIPES_DIR_NAME
from dontforget.generic import UT
from dontforget.settings import DEBUG, LOG_LEVEL

dirs = AppDirs(APP_NAME)

log_file = Path(dirs.user_log_dir) / "app.log"
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
        Quit = f"Quit {APP_NAME}"

    def __init__(self):
        super(DontForgetApp, self).__init__(self.DEFAULT_TITLE, quit_button=self.Menu.Quit.value)

        logger.debug("Creating scheduler")
        self.scheduler = BackgroundScheduler()

        self.config_file = Path(dirs.user_config_dir) / CONFIG_YAML
        if not self.config_file.exists():
            raise RuntimeError(f"Config file not found: {self.config_file}")

    @rumps.clicked(Menu.Preferences.value)
    def open_preferences(self, _):
        """Open the config file on the preferred editor."""
        run(["open", str(self.config_file)])

    def create_preferences_menu(self):
        """Create the preferences menu."""
        self.menu.add(self.Menu.Preferences.value)
        self.menu.add(rumps.separator)

    def start_scheduler(self) -> bool:
        """Start the scheduler."""
        logger.debug("Starting scheduler")
        self.scheduler.start()
        self.scheduler.print_jobs(out=log_file.open("a"))
        return True


@click.command()
def start_on_status_bar():
    """Don't forget to do your things."""
    from dontforget.default_pipes.gmail import GMailPlugin

    if DEBUG:
        rumps.debug_mode(True)

    app = DontForgetApp()
    if not GMailPlugin(app).init_app():
        sys.exit(1)
    app.create_preferences_menu()
    if not app.start_scheduler():
        sys.exit(2)
    app.run()


if __name__ == "__main__":
    start_on_status_bar()
