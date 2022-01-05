"""Command-line."""
import sys
from pathlib import Path

import click
import rumps
from joblib import Memory

from dontforget.app import DontForgetApp
from dontforget.settings import DEBUG, DEFAULT_DIRS, load_config_file

CACHE_DIR = Path(DEFAULT_DIRS.user_cache_dir)
JOBLIB_MEMORY = Memory(CACHE_DIR)  # , verbose=0


@click.group()
@click.option("--clear-cache", "-c", is_flag=True, default=False, help="Clear the cache before starting")
def main(clear_cache):
    """Don't forget to do your things."""
    if clear_cache:
        JOBLIB_MEMORY.clear()


@main.command()
def menu():
    """Show the app menu on the status bar."""
    from dontforget.default_pipes.gmail_plugin import GMailPlugin

    if DEBUG:
        rumps.debug_mode(True)

    app = DontForgetApp()
    config_yaml = load_config_file()

    for plugin_class in (GMailPlugin,):  # FIXME: TogglPlugin):
        plugin = plugin_class(config_yaml)
        app.plugins.append(plugin)

        app.menu.add(plugin.name)
        app.menu.add(rumps.separator)
        if not plugin.init_app(app):
            sys.exit(1)
    app.create_preferences_menu()
    if not app.start_scheduler():
        sys.exit(2)
    app.run()


def register_plugin_commands():
    """Register commands added by plugins."""
    from dontforget.default_pipes.toggl_plugin import TogglPlugin

    for command in TogglPlugin.register_cli_commands():
        main.add_command(command)


register_plugin_commands()
