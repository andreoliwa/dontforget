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
from ruamel.yaml import YAML

from dontforget import commands, pipes
from dontforget.constants import APP_NAME, CONFIG_YAML, DEFAULT_PIPES_DIR_NAME
from dontforget.generic import UT
from dontforget.settings import DEBUG, ProdConfig
from dontforget.views import blueprint

db = SQLAlchemy()
migrate = Migrate()  # pylint: disable=invalid-name


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
        GMail = "GMail:"
        Quit = "Quit Don't Forget"

    def __init__(self):
        super(DontForgetApp, self).__init__(UT.ReminderRibbon, quit_button=self.Menu.Quit.value)

        self.scheduler = BackgroundScheduler()

        dirs = AppDirs(APP_NAME)
        self.config_file = Path(dirs.user_config_dir) / CONFIG_YAML
        if not self.config_file.exists():
            raise RuntimeError(f"Config file not found: {self.config_file}")

        self.menu.add(self.Menu.Preferences.value)
        self.menu.add(rumps.separator)

    @rumps.clicked(Menu.Preferences.value)
    def open_preferences(self, _):
        """Open the config file on the preferred editor."""
        run(["open", str(self.config_file)])

    def start_scheduler(self) -> bool:
        """Start the scheduler."""
        if not self.add_gmail_jobs():
            return False

        self.scheduler.start()
        if DEBUG:
            self.scheduler.print_jobs()
        return True

    def add_gmail_jobs(self):
        """Add GMail jobs to the background scheduler."""
        from dontforget.default_pipes.gmail import GMailJob

        self.menu.add(self.Menu.GMail.value)

        all_authenticated = True
        yaml = YAML()
        config_data = yaml.load(self.config_file)
        for data in config_data["gmail"]:
            job = GMailJob(**data)
            if not job.authenticated:
                all_authenticated = False
            else:
                self.scheduler.add_job(job, "interval", misfire_grace_time=10, **job.trigger_args)

            submenu = rumps.MenuItem(job.gmail.email)
            submenu.add("Last checked on ???")  # FIXME: always show current time
            # FIXME: only fetch labels on the first run, so the UI shows up quickly
            submenu.add(rumps.separator)
            for label in sorted(job.gmail.labels):
                submenu.add(label)

            self.menu.add(submenu)

        self.menu.add(rumps.separator)
        return all_authenticated


def start_on_status_bar():
    """Main function."""
    if DEBUG:
        rumps.debug_mode(True)

    app = DontForgetApp()
    if not app.start_scheduler():
        sys.exit(1)
    app.run()
