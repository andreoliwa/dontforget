# -*- coding: utf-8 -*-
"""Database models."""
from datetime import datetime

import arrow
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
        return '<Chore {0!r} {1!r}, starting at {2}, repetition {3!r} from {4}>'.format(
            self.id, self.title, self.alarm_start, self.repetition,
            'completed' if self.repeat_from_completed else 'due date')

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
    STOPPED = 'killed'  # The chore is finished, no more alarms will be created. TODO Rename enum on database


ALARM_STATE_ENUM = db.Enum(
    AlarmState.UNSEEN, AlarmState.DISPLAYED, AlarmState.SKIPPED, AlarmState.SNOOZED, AlarmState.COMPLETED,
    AlarmState.STOPPED, name='alarm_state_enum')


class Alarm(SurrogatePK, Model):
    """An alarm for a chore."""

    __tablename__ = 'alarm'
    chore_id = reference_col('chore')
    current_state = db.Column(ALARM_STATE_ENUM, nullable=False, default=AlarmState.UNSEEN)
    next_at = db.Column(db.DateTime(), nullable=False)
    last_snooze = db.Column(db.String())
    updated_at = db.Column(db.DateTime(), nullable=False, onupdate=func.now(), default=func.now())

    chore = db.relationship('Chore')
    """:type: dontforget.models.Chore"""

    def __repr__(self):
        """Represent the alarm as a unique string."""
        return "<Alarm {!r} {!r} at '{}' (chore {!r})>".format(
            self.id, self.current_state, self.next_at, self.chore_id)

    @property
    def one_line(self):
        """Represent the alarm in one line."""
        next_at = arrow.get(self.next_at)
        return '{title} \u231b {due} ({human})'.format(
            title=self.chore.title, due=next_at.format('ddd MMM DD, YYYY HH:MM'), human=next_at.humanize())

    @classmethod
    def create_unseen(cls, chore_id, next_at, last_snooze=None):
        """Factory method to create an unseen alarm instance.

        The instance will be added to the session, but no commit will be issued.

        :param chore_id: Chore ID of the new alarm.
        :param next_at: Next date/time for the new alarm.
        :param str last_snooze: Last snooze time to be used as a suggestion for the new one.
        :return: An alarm.
        :rtype: Alarm
        """
        return cls.create(commit=False, chore_id=chore_id, next_at=next_at, current_state=AlarmState.UNSEEN,
                          last_snooze=last_snooze)

    def repeat(self, desired_state, snooze_repetition=None):
        """Set the desired state and create a new unseen alarm, based on the repetition settings in the related chore.

        An unseen alarm will only be created if there is a repetition, and if the chore is active.

        :param str desired_state: The desired state for the current alarm, before repetition.
        :param str snooze_repetition: Snooze repetition chosen by the user.
        :return: The current alarm if none created, or the newly created (and unseen) alarm instance.
        :rtype: Alarm
        """
        rv = self.update(commit=False, current_state=desired_state)

        next_at = None
        if snooze_repetition:
            next_at = next_dates(snooze_repetition, datetime.now())
        elif self.chore.repetition and self.chore.active():
            reference_date = self.updated_at if self.chore.repeat_from_completed else self.next_at
            next_at = next_dates(self.chore.repetition, reference_date)

        if next_at:
            rv = self.create_unseen(self.chore_id, next_at, snooze_repetition)

        db.session.commit()
        return rv

    def snooze(self, snooze_repetition):
        """Snooze this alarm using the desired repetition."""
        return self.repeat(AlarmState.SNOOZED, snooze_repetition)

    def skip(self):
        """Skip this alarm."""
        return self.repeat(AlarmState.SKIPPED)

    def complete(self):
        """Mark as completed."""
        return self.repeat(AlarmState.COMPLETED)

    def reset_unseen(self):
        """Mark as unseen again."""
        return self.update(current_state=AlarmState.UNSEEN)

    def stop(self):
        """Stop the series of alarms."""
        return self.update(current_state=AlarmState.STOPPED)
