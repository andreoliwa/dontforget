# -*- coding: utf-8 -*-
"""Database models."""
from sqlalchemy import or_
from sqlalchemy.sql.functions import func

from dontforget.database import Model, SurrogatePK, reference_col
from dontforget.extensions import db


class Chore(SurrogatePK, Model):
    """Anything you need to do, with or without due date, with or without repetition."""

    __tablename__ = 'chore'
    title = db.Column(db.String(), unique=True, nullable=False)
    alarm_start = db.Column(db.DateTime(), nullable=False)
    alarm_end = db.Column(db.DateTime())
    repetition = db.Column(db.String())
    repeat_from_completed = db.Column(db.Boolean(), nullable=False, default=False)

    alarms = db.relationship('Alarm')

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<Chore {!r}>'.format(self.title)

    def search_similar(self, min_chars=3):
        """Search for similar chores, using the title for comparison.

        Every word with at least ``min_chars`` will be considered and queried with a LIKE statement.
        It's kind of heavy for the database, but we don't expect a huge list of chores anyway.

        This is a simple algorithm right now, it can certainly evolve and improve if needed.

        :param int min_chars: Minimum number of characters for a word to be considered in the search.
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
    COMPLETED = 'completed'  # This repetition is done, but the chore is still active and will spawn alarms.
    KILLED = 'killed'  # The chore is finished, no more alarms will be created.


ALARM_STATE_ENUM = db.Enum(
    AlarmState.UNSEEN, AlarmState.DISPLAYED, AlarmState.SKIPPED, AlarmState.SNOOZED, AlarmState.COMPLETED,
    AlarmState.KILLED, name='alarm_state_enum')


class Alarm(SurrogatePK, Model):
    """An alarm for a chore."""

    __tablename__ = 'alarm'
    current_state = db.Column(ALARM_STATE_ENUM, nullable=False, default=AlarmState.UNSEEN)
    next_at = db.Column(db.DateTime(), nullable=False)
    chore_id = reference_col('chore')
    updated_at = db.Column(db.DateTime(), nullable=False, onupdate=func.now(), default=func.now())

    chore = db.relationship('Chore')

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<Alarm {!r} at {!r} (id {!r} chore_id {!r})>'.format(
            self.current_state, self.next_at, self.id, self.chore_id)

    def complete(self):
        """Mark as completed."""
        self.update(current_state=AlarmState.COMPLETED)
