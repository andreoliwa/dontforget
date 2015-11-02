# -*- coding: utf-8 -*-
"""Defines fixtures available to all tests."""
import pytest
from webtest import TestApp

from dontforget.app import create_app
from dontforget.database import db as _db
from dontforget.settings import TestConfig

from .factories import UserFactory


@pytest.yield_fixture(scope='function')
def app():
    """Application for the tests."""
    _app = create_app(TestConfig)
    ctx = _app.test_request_context()
    ctx.push()

    yield _app

    ctx.pop()


@pytest.fixture(scope='function')
def testapp(app):
    """A Webtest app."""
    return TestApp(app)


@pytest.yield_fixture(scope='function')
def db(app):
    """Database for the tests."""
    _db.app = app
    with app.app_context():
        _db.create_all()

    yield _db

    _db.drop_all()


@pytest.fixture
def user(db):
    """User for the tests."""
    user = UserFactory(password='myprecious')
    db.session.commit()
    return user
