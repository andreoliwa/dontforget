# -*- coding: utf-8 -*-
"""Database models."""
import arrow
from sqlalchemy import or_
from sqlalchemy.dialects import postgresql

from dontforget.app import db
from dontforget.database import CreatedUpdatedMixin, Model, SurrogatePK, reference_col
from dontforget.repetition import next_dates, right_now
from dontforget.settings import LOCAL_TIMEZONE
from dontforget.utils import DATETIME_FORMAT, UT


class Chore(SurrogatePK, CreatedUpdatedMixin, Model):
    """Anything you need to do, with or without due date, with or without repetition."""

    __tablename__ = 'chore'

    title = db.Column(db.String(), unique=True, nullable=False)
    due_at = db.Column(db.TIMESTAMP(timezone=True))
    alarm_at = db.Column(db.TIMESTAMP(timezone=True))
    alarm_end = db.Column(db.TIMESTAMP(timezone=True))
    repetition = db.Column(db.String())
    repeat_from_completed = db.Column(db.Boolean(), nullable=False, default=False)

    alarms = db.relationship('Alarm')

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<Chore {0!r} {1!r}, due at {2}, repetition {3!r} from {4}>'.format(
            self.id, self.title, self.due_at, self.repetition,
            'completed' if self.repeat_from_completed else 'due date')

    @property
    def one_line(self):
        """Represent the chore in one line."""
        due_string = ''
        if self.due_at:
            date = arrow.get(self.due_at).to(LOCAL_TIMEZONE)
            due_string = ' {icon} {due} ({human})'.format(
                icon=UT.Hourglass, due=date.format(DATETIME_FORMAT), human=date.humanize())

        repetition = ''
        if self.repetition:
            repetition = ' {icon} {repetition}'.format(icon='\u21ba', repetition=self.repetition)

        return '{title}{due}{repetition} {completed}'.format(
            title=self.title,
            due=due_string,
            repetition=repetition,
            completed='(from completed)' if self.repeat_from_completed else ''
        )

    @property
    def active(self):
        """Return True if the chore has an open end.

        Conditions:
        1. Has a due date in the past.
        2. No alarm end, or alarm end in the future.

        :rtype: bool
        """
        return self.due_at and self.due_at <= right_now() and (
            self.alarm_end is None or right_now() <= self.alarm_end)

    @classmethod
    def query_active(cls, reference_date=None):
        """Return a query filtered by active chores on a reference date (default now).

        1. Has a due date in the past.
        2. No alarm end, or alarm end in the future.
        """
        # pylint: disable=no-member
        valid_date = (reference_date or right_now())
        return cls.query.filter(
            cls.due_at <= valid_date,
            or_(cls.alarm_end.is_(None),
                cls.alarm_end >= valid_date))

    @classmethod
    def query_inactive(cls, reference_date=None):
        """Return a query filtered by inactive chores on a reference date (default now).

        One of those:
        1. Empty due date.
        2. Due date in the future (after the reference date).
        3. Alarm end in the past.
        """
        # pylint: disable=no-member
        valid_date = (reference_date or right_now())
        return cls.query.filter(or_(cls.due_at.is_(None),
                                    cls.due_at > valid_date,
                                    cls.alarm_end < valid_date))

    @classmethod
    def query_future(cls, reference_date=None):
        """Return a query filtered by future chores."""
        # pylint: disable=no-member
        return cls.query.filter(cls.due_at > (reference_date or right_now()))

    @classmethod
    def query_overdue(cls, reference_date=None):
        """Return a query filtered with overdue chores."""
        # pylint: disable=no-member
        return cls.query.filter(cls.alarm_at <= (reference_date or right_now()))\
            .order_by(Chore.alarm_at.desc(), Chore.due_at.desc())

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

    def repeat(self, action, snooze_repetition=None):
        """Set date fields and save alarm history with the desired action, based on the repetition settings.

        :param str action: The desired action for the saved alarm.
        :param str snooze_repetition: Snooze repetition chosen by the user.
        """
        Alarm.create(commit=False, chore_id=self.id, action=action, due_at=self.due_at, alarm_at=self.alarm_at,
                     snooze_repetition=snooze_repetition)

        due_at = None
        alarm_at = None
        now = right_now()
        if snooze_repetition:
            due_at = self.due_at
            alarm_at = next_dates(snooze_repetition, now)
        elif self.repetition and self.active:
            # Repeat from the current date or the original due date.
            due_at = alarm_at = next_dates(
                self.repetition, now if self.repeat_from_completed else self.due_at)

        self.update(commit=True, due_at=due_at, alarm_at=alarm_at)

    def complete(self):
        """Mark as completed."""
        return self.repeat(AlarmAction.COMPLETE)

    def snooze(self, snooze_repetition):
        """Snooze this alarm using the desired repetition."""
        return self.repeat(AlarmAction.SNOOZE, snooze_repetition)

    def jump(self):
        """Jump this alarm."""
        return self.repeat(AlarmAction.JUMP)

    def pause(self):
        """Pause the series of alarms by clearing the alarm dates."""
        return self.update(due_at=None, alarm_at=None)


class AlarmAction(object):
    """Possible actions for an alarm."""

    COMPLETE = 'complete'  # This repetition is done, but the chore is still active and will spawn alarms.
    SNOOZE = 'snooze'
    JUMP = 'jump'
    PAUSE = 'pause'  # The chore is finished, no more alarms will be created.


ALARM_ACTION_ENUM = postgresql.ENUM(
    AlarmAction.COMPLETE, AlarmAction.SNOOZE, AlarmAction.JUMP, AlarmAction.PAUSE, name='alarm_action_enum')


class Alarm(SurrogatePK, CreatedUpdatedMixin, Model):
    """History of alarms from a chore."""

    __tablename__ = 'alarm'

    chore_id = reference_col('chore')
    chore = db.relationship('Chore')
    """:type: dontforget.models.Chore"""

    action = db.Column(ALARM_ACTION_ENUM, nullable=False)
    due_at = db.Column(db.TIMESTAMP(timezone=True))
    alarm_at = db.Column(db.TIMESTAMP(timezone=True))
    snooze_repetition = db.Column(db.String())

    def __repr__(self):
        """Represent the alarm as a unique string."""
        return "<Alarm {!r} {!r} at '{}' (chore {!r})>".format(
            self.id, self.action, self.due_at, self.chore_id)
