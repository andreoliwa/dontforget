"""Click commands."""
import shlex
from subprocess import Popen

import click
from flask import current_app
from flask.cli import with_appcontext

from dontforget.config import FLASK_ENV, TELEGRAM_TOKEN
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
    """Start desktop app and Flask server.

    The desktop app is the menu icon on the status bar.
    The Flask server can be started with flask or docker.
    """
    from dontforget import menu
    from PyObjCTools import AppHelper

    if start_mode is None:
        start_mode = START_MODE_FLASK if FLASK_ENV == DEVELOPMENT else START_MODE_DOCKER

    if not icon:
        menu.hide_dock_icon()
        return

    command = FLASK_COMMAND if start_mode == START_MODE_FLASK else DOCKER_COMMAND
    process = Popen(shlex.split(command))

    desktop_app = menu.Sentinel.sharedApplication()
    AppHelper.runEventLoop(desktop_app)

    # TODO: this line is never reached; find a way to kill the process when we click "Quit" on the menu
    process.kill()


@click.command()
def db_refresh():
    """Refresh the database (drop and redo the upgrade)."""
    from dontforget.database import db_refresh as real_db_refresh

    real_db_refresh()


@click.command()
@with_appcontext
def telegram():
    """Run Telegram bot loop together with Flask main loop."""
    if not TELEGRAM_TOKEN:
        print("Telegram bot token is not defined (TELEGRAM_TOKEN)")
        return

    from dontforget.telegram_bot import main_loop

    main_loop(current_app)


@click.command()
def go_home():
    """Determine the time to go home."""
    from dontforget.home import go_home

    go_home()
