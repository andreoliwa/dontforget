#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Management script."""
import os
import sys
from glob import glob
from subprocess import call

from flask_migrate import MigrateCommand
from flask_script import Command, Manager, Option, Shell
from flask_script.commands import Clean, ShowUrls

from dontforget.app import create_app
from dontforget.database import db, db_refresh as real_db_refresh
from dontforget.settings import TELEGRAM_TOKEN, DevConfig, ProdConfig

CONFIG = ProdConfig if os.environ.get("DONTFORGET_ENV") == "prod" else DevConfig
HERE = os.path.abspath(os.path.dirname(__file__))
TEST_PATH = os.path.join(HERE, "tests")

app = create_app(CONFIG)  # pylint: disable=invalid-name
manager = Manager(app)  # pylint: disable=invalid-name


def _make_context():
    """Return context dict for a shell session so you can access app and db."""
    return {"app": app, "db": db}


@manager.command
def test():
    """Run the tests."""
    import pytest

    exit_code = pytest.main([TEST_PATH, "--verbose"])
    return exit_code


@manager.command
def db_refresh():
    """Refresh the database (drop and redo the upgrade)."""
    real_db_refresh()


class Lint(Command):
    """Lint and check code style with flake8, isort and, optionally, pylint."""

    def get_options(self):
        """Command line options."""
        return (
            Option(
                "-f",
                "--fix-imports",
                action="store_true",
                dest="fix_imports",
                default=False,
                help="Fix imports using isort, before linting",
            ),
            Option(
                "-p",
                "--pylint",
                action="store_true",
                dest="use_pylint",
                default=False,
                help="Use pylint after flake8, for an extended strict check",
            ),
        )

    def run(self, fix_imports, use_pylint):  # pylint: disable=arguments-differ,method-hidden
        """Run command."""
        skip = ["requirements", "docker", "_sandbox"]
        root_files = glob("*.py")
        root_directories = [name for name in next(os.walk("."))[1] if not name.startswith(".")]
        files_and_directories = [arg for arg in root_files + root_directories if arg not in skip]

        def execute_tool(description, *args):
            """Execute a checking tool with its arguments."""
            command_line = list(args) + files_and_directories
            print("{0}: {1}".format(description, " ".join(command_line)))
            rv = call(command_line)
            if rv != 0:
                exit(rv)

        if fix_imports:
            execute_tool("Fixing import order", "isort", "-rc")
        execute_tool("Checking code style", "flake8")
        if use_pylint:
            execute_tool("Checking code style", "pylint", "--rcfile=.pylintrc")


@manager.command
def telegram():
    """Run Telegram bot loop together with Flask main loop."""
    if not TELEGRAM_TOKEN:
        print("Telegram bot token is not defined (TELEGRAM_TOKEN)")
        return

    from dontforget.telegram_bot import main_loop

    main_loop(app)


@manager.command
def menu():
    """Display the menu of the application."""
    from PyObjCTools import AppHelper
    from dontforget.menu import Sentinel, suppress_dock_icon

    if (len(sys.argv) > 1) and (sys.argv[1] == "--suppress-dock-icon"):
        suppress_dock_icon()
    else:
        app = Sentinel.sharedApplication()
        AppHelper.runEventLoop(app)


@manager.command
def go_home():
    """Determine the time to go home."""
    from dontforget.home import go_home

    go_home()


manager.add_command("shell", Shell(make_context=_make_context))
manager.add_command("db", MigrateCommand)
manager.add_command("urls", ShowUrls())
manager.add_command("clean", Clean())
manager.add_command("lint", Lint())

if __name__ == "__main__":
    manager.run()
