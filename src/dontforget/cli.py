"""Command-line."""
import sys
from pathlib import Path
from typing import List, Tuple

import click
import rumps
from joblib import Memory

from dontforget.app import DontForgetApp
from dontforget.pipes import PIPE_CONFIG, Pipe, PipeType
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
    from dontforget.default_pipes.toggl_plugin import TogglPlugin

    if DEBUG:
        rumps.debug_mode(True)

    app = DontForgetApp()
    config_yaml = load_config_file()

    for plugin_class in (GMailPlugin, TogglPlugin):
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


@main.group()
def pipe():
    """Pipes that pull data from a source and push it to a target."""
    from dontforget.app import load_plugins

    load_plugins()


@pipe.command()
@click.option("--all", "-a", "which", flag_value=PipeType.ALL, default=True, help="All pipes")
@click.option("--default", "-d", "which", flag_value=PipeType.DEFAULT, help="Default pipes")
@click.option("--user", "-u", "which", flag_value=PipeType.USER, help="User pipes")
def ls(which: PipeType):
    """List default and user pipes."""
    if which == PipeType.DEFAULT or which == PipeType.ALL:
        PIPE_CONFIG.echo("Default pipes", True)
    if which == PipeType.USER or which == PipeType.ALL:
        PIPE_CONFIG.echo("User pipes", False)


@pipe.command()
@click.argument("partial_names", nargs=-1)
def run(partial_names: Tuple[str, ...]):
    """Run the chosen pipes."""
    chosen_pipes: List[Pipe] = []
    for partial_name in partial_names:
        chosen_pipes.extend(PIPE_CONFIG.get_pipes(partial_name))
    if not chosen_pipes:
        chosen_pipes = PIPE_CONFIG.user_pipes
    for chosen_pipe in sorted(chosen_pipes):
        chosen_pipe.run()
