# -*- coding: utf-8 -*-
# pylint: disable=unnecessary-lambda
"""Factories to help in tests."""
from datetime import datetime, timedelta

from factory import LazyAttribute, PostGenerationMethodCall, Sequence, SubFactory
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker

from dontforget.database import db
from dontforget.models import Alarm, Chore
from dontforget.user.models import User

fake = Faker()  # pylint: disable=invalid-name

TODAY = datetime.now()
NEXT_WEEK = TODAY + timedelta(days=7)
LAST_WEEK = TODAY - timedelta(days=7)
YESTERDAY = TODAY - timedelta(days=1)


class BaseFactory(SQLAlchemyModelFactory):
    """Base factory."""

    class Meta:
        """Factory configuration."""

        abstract = True
        sqlalchemy_session = db.session


class UserFactory(BaseFactory):
    """User factory."""

    username = Sequence(lambda n: 'user{0}'.format(n))
    email = Sequence(lambda n: 'user{0}@example.com'.format(n))
    password = PostGenerationMethodCall('set_password', 'example')
    active = True

    class Meta:
        """Factory configuration."""

        model = User


class ChoreFactory(BaseFactory):
    """Chore factory."""

    title = LazyAttribute(lambda x: ' '.join(fake.words(10)))
    alarm_start = LazyAttribute(lambda x: fake.date_time_between('-30d', '-20d'))

    class Meta:
        """Factory configuration."""

        model = Chore


class AlarmFactory(BaseFactory):
    """Alarm factory."""

    next_at = LazyAttribute(lambda x: fake.date_time_between('-5d', '-1d'))
    chore = SubFactory(ChoreFactory)

    class Meta:
        """Factory configuration."""

        model = Alarm
