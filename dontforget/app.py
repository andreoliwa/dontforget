"""The app module, containing the app factory function."""
import logging
import sys
from enum import Enum
from pathlib import Path
from subprocess import run

import rumps
from appdirs import AppDirs
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from pluginbase import PluginBase

from dontforget import commands, pipes
from dontforget.constants import APP_NAME, CONFIG_YAML, DEFAULT_PIPES_DIR_NAME
from dontforget.generic import UT
from dontforget.settings import DEBUG, LOG_LEVEL, ProdConfig
from dontforget.views import blueprint

db = SQLAlchemy()
migrate = Migrate()  # pylint: disable=invalid-name

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)


def create_app(config_object=ProdConfig):
    """An application factory, as explained here: http://flask.pocoo.org/docs/patterns/appfactories/.

    :param config_object: The configuration object to use.
    """
    app = Flask(__name__)
    app.config.from_object(config_object)
    register_blueprints(app)
    register_extensions(app)
    # TODO: feat: add missing favicon
    # register_errorhandlers(app)
    logging.basicConfig()
    register_commands(app)
    load_plugins()
    return app


def register_blueprints(app):
    """Register Flask blueprints."""
    app.register_blueprint(blueprint)


def register_extensions(app):
    """Register Flask extensions."""
    db.init_app(app)
    migrate.init_app(app, db)
    return None


def register_errorhandlers(app):
    """Register error handlers."""

    def render_error(error):
        """Render error template."""
        # If a HTTPException, pull the `code` attribute; default to 500
        error_code = getattr(error, "code", 500)
        # TODO: fix: error templates
        return render_template("{}.html".format(error_code)), error_code

    for errcode in [401, 404, 500]:
        app.errorhandler(errcode)(render_error)
    return None


def register_commands(app):
    """Register Click commands."""
    app.cli.add_command(commands.desktop)
    app.cli.add_command(commands.db_refresh)
    app.cli.add_command(commands.telegram)
    app.cli.add_command(commands.go_home)
    app.cli.add_command(pipes.pipe)


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

    class Menu(Enum):
        """Menu items."""

        Preferences = "Preferences..."
        Quit = f"Quit {APP_NAME}"

    def __init__(self):
        super(DontForgetApp, self).__init__(UT.ReminderRibbon, quit_button=self.Menu.Quit.value)

        logger.debug("Creating scheduler")
        self.scheduler = BackgroundScheduler()

        logger.debug("Reading config file")
        dirs = AppDirs(APP_NAME)
        self.config_file = Path(dirs.user_config_dir) / CONFIG_YAML
        if not self.config_file.exists():
            raise RuntimeError(f"Config file not found: {self.config_file}")

        logger.debug("Adding preferences menu")
        self.menu.add(self.Menu.Preferences.value)
        self.menu.add(rumps.separator)

    @rumps.clicked(Menu.Preferences.value)
    def open_preferences(self, _):
        """Open the config file on the preferred editor."""
        run(["open", str(self.config_file)])

    def start_scheduler(self) -> bool:
        """Start the scheduler."""
        logger.debug("Starting scheduler")
        self.scheduler.start()
        if DEBUG:
            self.scheduler.print_jobs()
        return True


def start_on_status_bar():
    """Main function."""
    from dontforget.default_pipes.gmail import GMailPlugin

    if DEBUG:
        rumps.debug_mode(True)

    app = DontForgetApp()
    GMailPlugin().init_app(app)
    if not app.start_scheduler():
        sys.exit(1)
    app.run()
