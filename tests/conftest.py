# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name
"""Defines fixtures available to all tests."""
import os
from typing import Iterator

import pytest
from flask import Flask
from flask.ctx import AppContext
from flask_migrate import Migrate

from dontforget.app import create_app
from dontforget.config import REFRESH_TEST_DATABASE, TestConfig
from dontforget.database import db, db_refresh


@pytest.yield_fixture(scope="session", autouse=True)
def session_tear_down(request):
    """Create a fake app to refresh db, drop app and after execution create a new fake drop db and drop app."""
    if not REFRESH_TEST_DATABASE:
        yield
        return

    def tear_down_app(app_generator):
        """Consume app generator."""
        try:
            next(app_generator)
        except StopIteration:
            # Teardown app
            pass
        else:
            raise RuntimeError("App fixture has more than one yield.")

    app_ = AppFactory.generator(request)

    Migrate(next(app_), db, os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "migrations"))
    db_refresh(short=True)
    tear_down_app(app_)

    # Halt function until pytest calls the teardown.
    yield
    app_ = AppFactory.generator(request)
    next(app_)
    tear_down_app(app_)


@pytest.yield_fixture(scope="function")
def app(request) -> Iterator[Flask]:
    """App fixture. This code is copied from :py:meth:`AppFactory.generator()` above.

    It can't be called neither with `yield`, `return` or something other way.
    It only works when it's copy/pasted and written like this.
    """
    app_factory = AppFactory()
    yield app_factory.create_new_app()
    app_factory.cleanup(request)


class AppFactory:
    """App factory that can be used in fixtures, either returning a generator or a new app instance.

    Since pytest 4.0, fixtures can't be called directly and it raises pytest.RemovedInPytest4Warning.
    We need this class to reuse app creation code: different needs in different fixtures.

    See https://github.com/pytest-dev/pytest/blob/master/CHANGELOG.rst#pytest-400-2018-11-13
    """

    new_app: Flask
    new_app_context: AppContext

    def __init__(self) -> None:
        """Init the app, context and patched functions."""
        self.original_commit_method = None

    def create_new_app(self) -> Flask:
        """Create a new app, configuring it for tests and patching necessary methods."""
        os.environ["SQLALCHEMY_POOL_SIZE"] = "1"
        new_app = create_app(TestConfig)

        # If testing while a localhost tunnel like https://ngrok.com/ or https://pagekite.net/,
        # you can set a server name on the .env file.
        # If there is no server name configured, assume the default 'localhost'.
        if not new_app.config["SERVER_NAME"]:
            new_app.config["SERVER_NAME"] = "localhost.localdomain"

        self.new_app_context = new_app.app_context()
        self.new_app_context.push()

        def commit():
            """Flush and expire caches."""
            db.session.flush()
            db.session.expire_all()

        self.original_commit_method = db.session.commit
        db.session.commit = commit

        self.new_app = new_app
        return self.new_app

    def cleanup(self, request) -> None:
        """Perform app cleanup after yield, restoring patched methods and doing other stuff."""
        db.session.commit = self.original_commit_method
        db.session.remove()
        db.engine.dispose()

        self.new_app_context.pop()

    @classmethod
    def generator(cls, request) -> Iterator[Flask]:
        """Return a generator instead of an app instance. Used by the :py:meth:`session_tear_down()` fixture."""
        app_factory = cls()
        yield app_factory.create_new_app()
        app_factory.cleanup(request)
