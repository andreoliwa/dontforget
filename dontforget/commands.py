"""Click commands."""
import shlex
from subprocess import Popen

import click
from flask.cli import with_appcontext
from prettyconf import config

from dontforget.constants import DEVELOPMENT, DOCKER_COMMAND, FLASK_COMMAND, START_MODE_DOCKER, START_MODE_FLASK


@click.command()
@click.option(
    "--flask", "start_mode", flag_value=START_MODE_FLASK, help=f"Start the web server using {FLASK_COMMAND!r}"
)
@click.option(
    "--docker", "start_mode", flag_value=START_MODE_DOCKER, help=f"Start the web server using {DOCKER_COMMAND!r}"
)
@click.option("--icon/--no-icon", default=True, help="Show or hide the status bar icon.")
@with_appcontext
def desktop(start_mode: str, icon: bool):
    """Start the desktop app (menu icon on the status bar) and the Flask server as well."""
    from dontforget import menu
    from PyObjCTools import AppHelper

    if start_mode is None:
        start_mode = START_MODE_FLASK if config("FLASK_ENV") == DEVELOPMENT else START_MODE_DOCKER

    if not icon:
        menu.hide_dock_icon()
        return

    command = FLASK_COMMAND if start_mode == START_MODE_FLASK else DOCKER_COMMAND
    process = Popen(shlex.split(command))

    desktop_app = menu.Sentinel.sharedApplication()
    AppHelper.runEventLoop(desktop_app)

    # TODO: this line is never reached; find a way to kill the process when we click "Quit" on the menu
    process.kill()
