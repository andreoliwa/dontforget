# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name
"""Defines fixtures available to all tests."""
import os

import pytest
from flask_migrate import Migrate
from webtest import TestApp

from dontforget.app import create_app
from dontforget.database import db, db_refresh
from dontforget.settings import TEST_REFRESH_DATABASE, TestConfig


@pytest.yield_fixture(scope='session', autouse=True)
def tear_down():
    """Create a fake app to refresh db, drop app and after execution create a new fake drop db and drop app."""
    if not TEST_REFRESH_DATABASE:
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
            raise RuntimeError('App fixture has more than one yield.')

    app_ = app()

    Migrate(next(app_), db, os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'migrations'))
    db_refresh(short=True)
    tear_down_app(app_)

    # Halt function until pytest calls the teardown.
    yield
    app_ = app()
    next(app_)
    tear_down_app(app_)


@pytest.yield_fixture(scope='function')
def app():
    """An application for the tests."""
    _app = create_app(TestConfig)
    context = _app.app_context()
    context.push()

    def fake_commit():
        """Don't commit on tests; only flush and expire caches."""
        db.session.flush()
        db.session.expire_all()

    old_commit = db.session.commit
    db.session.commit = fake_commit

    yield _app

    db.session.commit = old_commit
    db.session.remove()
    db.engine.dispose()

    context.pop()


@pytest.fixture(scope='function')
def testapp(app):
    """A Webtest app."""
    return TestApp(app)
