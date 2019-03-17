#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Management script."""
import os

from flask_script import Manager

from dontforget.app import create_app
from dontforget.database import db_refresh as real_db_refresh
from dontforget.settings import TELEGRAM_TOKEN, DevConfig, ProdConfig

CONFIG = ProdConfig if os.environ.get("DONTFORGET_ENV") == "prod" else DevConfig
HERE = os.path.abspath(os.path.dirname(__file__))
TEST_PATH = os.path.join(HERE, "tests")

app = create_app(CONFIG)  # pylint: disable=invalid-name
manager = Manager(app)  # pylint: disable=invalid-name


@manager.command
def db_refresh():
    """Refresh the database (drop and redo the upgrade)."""
    real_db_refresh()


@manager.command
def telegram():
    """Run Telegram bot loop together with Flask main loop."""
    if not TELEGRAM_TOKEN:
        print("Telegram bot token is not defined (TELEGRAM_TOKEN)")
        return

    from dontforget.telegram_bot import main_loop

    main_loop(app)


@manager.command
def go_home():
    """Determine the time to go home."""
    from dontforget.home import go_home

    go_home()


if __name__ == "__main__":
    manager.run()
