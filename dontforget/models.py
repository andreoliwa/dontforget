# -*- coding: utf-8 -*-
"""Database models."""
import arrow
from sqlalchemy import and_, or_
from sqlalchemy.dialects import postgresql

from dontforget.app import db
from dontforget.database import CreatedUpdatedMixin, Model, SurrogatePK, reference_col
from dontforget.repetition import next_dates, right_now
from dontforget.utils import DATETIME_FORMAT, TIMEZONE


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
        return '{title} / from {start} to {end} / {repetition} {completed}'.format(
            title=self.title,
            start=arrow.get(self.alarm_start).to(TIMEZONE).format(DATETIME_FORMAT),
            end=arrow.get(self.alarm_end).to(TIMEZONE).format(DATETIME_FORMAT) if self.alarm_end else 'infinity',
            repetition=self.repetition or 'Once',
            completed='(from completed)' if self.repeat_from_completed else ''
        )

    def has_open_end(self):
        """Return True if the chore has an open end.

        Conditions:
        1. Alarm end empty, or greater than/equal to right now.

        :rtype: bool
        """
        return self.alarm_end is None or right_now() <= self.alarm_end

    @classmethod
    def active_expression(cls):
        """Return a SQL expression to check if the chore is active right now.

        Use almost the the same logic as ``active()`` above.
        One addition: also returns new chores which still don't have any alarm.

        :return: Return a binary expression to be used in SQLAlchemy queries.
        """
        now = right_now()
        return and_(Alarm.id.is_(None),
                    or_(cls.alarm_end.is_(None), now <= cls.alarm_end))

    @classmethod
    def query_active(cls, reference_date=None):
        """Return a query filtered by active chores."""
        # pylint: disable=no-member
        return cls.query.filter(or_(cls.alarm_end.is_(None), (reference_date or right_now()) <= cls.alarm_end))

    @classmethod
    def query_inactive(cls, reference_date=None):
        """Return a query filtered by inactive chores."""
        # pylint: disable=no-member
        return cls.query.filter((reference_date or right_now()) > cls.alarm_end)

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
        elif self.repetition and self.has_open_end():
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

    def finish(self):
        """Stop the series of alarms (save one last alarm in the history)."""
        # TODO Augusto:
        return self.repeat(AlarmAction.FINISH)


class AlarmAction(object):
    """Possible actions for an alarm."""

    COMPLETE = 'complete'  # This repetition is done, but the chore is still active and will spawn alarms.
    SNOOZE = 'snooze'
    JUMP = 'jump'
    FINISH = 'finish'  # The chore is finished, no more alarms will be created.


ALARM_ACTION_ENUM = postgresql.ENUM(
    AlarmAction.COMPLETE, AlarmAction.SNOOZE, AlarmAction.JUMP, AlarmAction.FINISH, name='alarm_action_enum')


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

    @property
    def one_line(self):
        """Represent the alarm in one line."""
        reference_date = arrow.get(self.original_at or self.next_at).to(TIMEZONE)
        return '{title} \u231b {due} ({human}) \u21ba {repetition} {completed}'.format(
            title=self.chore.title,
            due=reference_date.format(DATETIME_FORMAT),
            human=reference_date.humanize(),
            repetition=self.chore.repetition or 'Once',
            completed='(from completed)' if self.chore.repeat_from_completed else ''
        )
