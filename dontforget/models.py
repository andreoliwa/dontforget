# -*- coding: utf-8 -*-
"""Database models."""
from sqlalchemy import or_

from dontforget.database import Model, SurrogatePK, reference_col
from dontforget.extensions import db


class Chore(SurrogatePK, Model):
    """Anything you need to do, with or without due date, with or without repetition."""

    __tablename__ = 'chore'
    title = db.Column(db.String(), unique=True, nullable=False)
    alarm_start = db.Column(db.DateTime(), nullable=False)
    alarm_end = db.Column(db.DateTime())

    alarms = db.relationship('Alarm')

    # TODO Uncomment columns when they are needed.
    # description = db.Column(db.String())
    # labels = db.Column(db.String())
    # repetition = db.Column(db.String())
    # created_at
    # modified_at

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
        like_expressions = [Chore.title.ilike('%{0}%'.format(term.lower()))
                            for term in self.title.split(' ') if len(term) >= min_chars]
        query = Chore.query.filter(or_(*like_expressions))  # pylint: disable=no-member
        return query.all()


class AlarmState(object):
    """Possible states for an alarm."""

    UNSEEN = 'unseen'
    DISPLAYED = 'displayed'
    SKIPPED = 'skipped'
    SNOOZED = 'snoozed'
    DONE = 'done'

ALARM_STATE_ENUM = db.Enum(
    AlarmState.UNSEEN, AlarmState.DISPLAYED, AlarmState.SKIPPED, AlarmState.SNOOZED, AlarmState.DONE,
    name='alarm_state_enum')


class Alarm(SurrogatePK, Model):
    """An alarm for a chore."""

    __tablename__ = 'alarm'
    current_state = db.Column(ALARM_STATE_ENUM, nullable=False, default=AlarmState.UNSEEN)
    next_at = db.Column(db.DateTime(), nullable=False)
    chore_id = reference_col('chore')

    chore = db.relationship('Chore')

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<Alarm {!r} at {!r}>'.format(self.current_state, self.next_at)
