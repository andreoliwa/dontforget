# -*- coding: utf-8 -*-
# pylint: disable=unnecessary-lambda
"""Factories to help in tests."""
from factory import LazyAttribute, PostGenerationMethodCall, Sequence
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker

from dontforget.database import db
from dontforget.models import Chore
from dontforget.user.models import User

fake = Faker()  # pylint: disable=invalid-name
fake.seed(666)


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

    title = LazyAttribute(lambda x: ' '.join(fake.words(4)))

    class Meta:
        """Factory configuration."""

        model = Chore
