# -*- coding: utf-8 -*-
"""Factories to help in tests."""
from datetime import timedelta

from factory import LazyAttribute, Sequence, SubFactory
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker

from dontforget.database import db
from dontforget.models import Alarm, Chore
from dontforget.repetition import right_now

fake = Faker()  # pylint: disable=invalid-name

TODAY = right_now().datetime
NEXT_WEEK = TODAY + timedelta(days=7)
LAST_WEEK = TODAY - timedelta(days=7)
YESTERDAY = TODAY - timedelta(days=1)


class BaseFactory(SQLAlchemyModelFactory):
    """Base factory."""

    class Meta:
        """Factory configuration."""

        abstract = True
        sqlalchemy_session = db.session


class ChoreFactory(BaseFactory):
    """Chore factory."""

    title = Sequence(lambda n: '{0} {1}'.format(fake.word, n))

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
