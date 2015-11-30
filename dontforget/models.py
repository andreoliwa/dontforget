# -*- coding: utf-8 -*-
"""Database models."""
from datetime import datetime

from sqlalchemy import and_, or_
from sqlalchemy.sql.functions import func

from dontforget.database import Model, SurrogatePK, reference_col
from dontforget.extensions import db
from dontforget.repetition import next_dates


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

    def active(self, right_now=None):
        """Return True if the chore is active right now.

        Conditions for an active chore:
        1. Alarm start older than right now;
        2. Alarm end empty, or greater than/equal to right now.

        :param datetime right_now: A reference date. If not provided (default), assumes the current date/time.
        :return: Return True if the chore is active right now.
        :rtype: bool
        """
        if not right_now:
            right_now = datetime.now()
        return self.alarm_start <= right_now and (self.alarm_end is None or right_now <= self.alarm_end)

    @classmethod
    def active_expression(cls, right_now=None):
        """Return a SQL expression to check if the chore is active right now.

        Use the same logic as ``active()`` above.

        :param datetime right_now: A reference date. If not provided (default), assumes the current date/time.
        :return: Return a binary expression to be used in SQLAlchemy queries.
        """
        if not right_now:
            right_now = datetime.now()
        return and_(cls.alarm_start <= right_now, or_(cls.alarm_end.is_(None), right_now <= cls.alarm_end))

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
    """:type: dontforget.models.Chore"""

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<Alarm {!r} at {!r} (id {!r} chore_id {!r})>'.format(
            self.current_state, self.next_at, self.id, self.chore_id)

    @classmethod
    def create_unseen(cls, chore_id, next_at):
        """Factory method to create an unseen alarm instance.

        The instance will be added to the session, but no commit will be issued.

        :param chore_id: Chore ID of the new alarm.
        :param next_at: Next date/time for the new alarm.
        :return: An alarm.
        :rtype: Alarm
        """
        return cls.create(commit=False, chore_id=chore_id, next_at=next_at, current_state=AlarmState.UNSEEN)

    def repeat(self, desired_state, manual_repetition=None):
        """Set the desired state and create a new unseen alarm, based on the repetition settings in the related chore.

        An unseen alarm will only be created if there is a repetition, and if the chore is active.

        :param AlarmState desired_state: The desired state for the current alarm, before repetition.
        :return: The current alarm if none created, or the newly created (and unseen) alarm instance.
        :rtype: Alarm
        """
        rv = self.update(commit=False, current_state=desired_state)

        next_at = None
        if manual_repetition:
            next_at = next_dates(manual_repetition, datetime.now())
        elif self.chore.repetition and self.chore.active():
            reference_date = self.updated_at if self.chore.repeat_from_completed else self.next_at
            next_at = next_dates(self.chore.repetition, reference_date)

        if next_at:
            rv = self.create_unseen(self.chore_id, next_at)

        db.session.commit()
        return rv

    def snooze(self, repetition):
        """Snooze this alarm using the desired repetition."""
        return self.repeat(AlarmState.SNOOZED, 'Every ' + repetition)

    def skip(self):
        """Skip this alarm."""
        return self.repeat(AlarmState.SKIPPED)

    def complete(self):
        """Mark as completed."""
        return self.repeat(AlarmState.COMPLETED)
