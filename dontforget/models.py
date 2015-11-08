# -*- coding: utf-8 -*-
"""Database models."""
from sqlalchemy import or_

from .database import Model, SurrogatePK
from .extensions import db


class Chore(SurrogatePK, Model):
    """Anything you need to do, with or without due date, with or without repetition."""

    __tablename__ = 'chore'
    title = db.Column(db.String(), unique=True, nullable=False)

    # TODO Uncomment columns when they are needed.
    # description = db.Column(db.String())
    # labels = db.Column(db.String())
    # repetition = db.Column(db.String())
    # alarm_start = db.Column(db.DateTime(), nullable=False)
    # alarm_end = db.Column(db.DateTime())
    # next_at
    # created_at
    # modified_at
    # alarms = relationship('Alarm', backref='alarms')

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<Chore {!r}>'.format(self.title)

    def search_similar(self, min_chars: int=3):
        """Search for similar chores, using the title for comparison.

        Every word with at least ``min_chars`` will be considered and queried with a LIKE statement.
        It's kind of heavy for the database, but we don't expect a huge list of chores anyway.

        This is a simple algorithm right now, it can certainly evolve and improve if needed.

        :param min_chars: Minimum number of characters for a word to be considered in the search.
        :return: A list of chores that were found, or an empty list.
        :rtype: list[Chore]
        """
        like_expressions = [Chore.title.ilike('%{}%'.format(term.lower()))
                            for term in self.title.split(' ') if len(term) >= min_chars]
        query = Chore.query.filter(or_(*like_expressions))  # pylint: disable=no-member
        return query.all()
