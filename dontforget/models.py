"""Database models."""
from datetime import timedelta

import arrow
from sqlalchemy import and_, or_
from sqlalchemy.dialects import postgresql

from dontforget.app import db
from dontforget.database import CreatedUpdatedMixin, Model, SurrogatePK, reference_col
from dontforget.generic import DATETIME_FORMAT, UT
from dontforget.repetition import next_dates, right_now
from dontforget.settings import LOCAL_TIMEZONE, LONG_OVERDUE, MEDIUM_OVERDUE


class Chore(SurrogatePK, CreatedUpdatedMixin, Model):
    """Anything you need to do, with or without due date, with or without repetition."""

    __tablename__ = "chore"

    title = db.Column(db.String(), unique=True, nullable=False)
    due_at = db.Column(db.TIMESTAMP(timezone=True))
    alarm_at = db.Column(db.TIMESTAMP(timezone=True))
    alarm_end = db.Column(db.TIMESTAMP(timezone=True))
    repetition = db.Column(db.String())
    repeat_from_completed = db.Column(db.Boolean(), nullable=False, default=False)

    alarms = db.relationship("Alarm")

    def __repr__(self):
        """Represent instance as a unique string."""
        return "<Chore {!r} {!r}, due at {}, repetition {!r} from {}>".format(
            self.id, self.title, self.due_at, self.repetition, "completed" if self.repeat_from_completed else "due date"
        )

    @property
    def one_line(self):
        """Represent the chore in one line."""
        main_icon = UT.WhiteExclamationMarkOrnament

        due_str = ""
        if self.due_at:
            now = right_now()
            long_overdue = now - timedelta(days=LONG_OVERDUE)
            medium_overdue = now - timedelta(days=MEDIUM_OVERDUE)

            if self.due_at > now:
                main_icon = UT.WhiteHeavyCheckMark
            elif self.due_at < long_overdue:
                main_icon = UT.Fire
            elif self.due_at < medium_overdue:
                main_icon = UT.DoubleExclamationMark
            else:
                main_icon = UT.HeavyExclamationMarkSymbol

            local_due_at = arrow.get(self.due_at).to(LOCAL_TIMEZONE)
            due_str = " {icon} {due} ({human})".format(
                icon=UT.Hourglass, due=local_due_at.format(DATETIME_FORMAT), human=local_due_at.humanize()
            )

        repetition_str = ""
        if self.repetition:
            repetition_str = " {icon} {repetition}{completed}".format(
                icon=UT.Cyclone,
                repetition=self.repetition,
                completed=" (from completed)" if self.repeat_from_completed else "",
            )

        return "{icon} /id_{id}: {title}{repetition}{due}".format(
            icon=main_icon, id=self.id, title=self.title, repetition=repetition_str, due=due_str
        )

    def overdue(self, date=None):
        """Overdue chore: due date exists and it's in the past."""
        return self.due_at and self.due_at <= right_now(date) and not self.expired()

    @classmethod
    def expression_overdue(cls, date=None):
        """SQL expression for overdue."""
        return and_(cls.due_at <= right_now(date).datetime, cls.expression_not_expired(date))

    def expired(self, date=None):
        """Expired chore: has an alarm end and it's over its alarm end date."""
        return self.alarm_end and self.alarm_end < right_now(date)

    @classmethod
    def expression_expired(cls, date=None):
        """SQL expression for expired."""
        return cls.alarm_end < right_now(date).datetime

    @classmethod
    def expression_not_expired(cls, date=None):
        """SQL expression for not expired."""
        return or_(cls.alarm_end.is_(None), cls.alarm_end >= right_now(date).datetime)

    def future(self, date=None):
        """Future chore: due date in the future."""
        return self.due_at > right_now(date)

    @classmethod
    def expression_future(cls, date=None):
        """SQL expression for future."""
        return cls.due_at > right_now(date).datetime

    @classmethod
    def query_active(cls, date=None):
        """Return a query with active chores: has a due date and it's not expired."""
        # pylint: disable=no-member
        return cls.query.filter(cls.due_at.isnot(None), cls.expression_not_expired(date))

    @classmethod
    def query_inactive(cls, date=None):
        """Return a query with inactive chores: no due date or expired."""
        # pylint: disable=no-member
        return cls.query.filter(or_(cls.due_at.is_(None), cls.expression_expired(date)))

    @classmethod
    def query_future(cls, date=None):
        """Return a query filtered by future chores."""
        # pylint: disable=no-member
        return cls.query.filter(cls.due_at > right_now(date).datetime)

    @classmethod
    def query_overdue(cls, date=None):
        """Return a query filtered with overdue chores."""
        # pylint: disable=no-member
        return cls.query.filter(cls.alarm_at <= right_now(date).datetime).order_by(
            Chore.alarm_at.desc(), Chore.due_at.desc()
        )

    def search_similar(self, min_chars=3):
        """Search for similar chores, using the title for comparison.

        Every word with at least ``min_chars`` will be considered and queried with a LIKE statement.
        It's kind of heavy for the database, but we don't expect a huge list of chores anyway.

        This is a simple algorithm right now, it can certainly evolve and improve if needed.

        :param int min_chars: Minimum number of characters for a word to be considered in the search.
        :return: A list of chores that were found, or an empty list.
        :rtype: list[Chore]
        """
        like_expressions = [
            Chore.title.ilike("%{}%".format(term.lower())) for term in self.title.split(" ") if len(term) >= min_chars
        ]
        query = Chore.query.filter(or_(*like_expressions))  # pylint: disable=no-member
        return query.all()

    def repeat(self, action, snooze_repetition=None):
        """Set date fields and save alarm history with the desired action, based on the repetition settings.

        :param str action: The desired action for the saved alarm.
        :param str snooze_repetition: Snooze repetition chosen by the user.
        """
        Alarm.create(
            commit=False,
            chore_id=self.id,
            action=action,
            due_at=self.due_at,
            alarm_at=self.alarm_at,
            snooze_repetition=snooze_repetition,
        )

        due_at = None
        alarm_at = None
        now = right_now().datetime
        if snooze_repetition:
            due_at = self.due_at
            alarm_at = next_dates(snooze_repetition, now)
        elif self.repetition and not self.expired():
            # Repeat from the current date or the original due date.
            due_at = alarm_at = next_dates(self.repetition, now if self.repeat_from_completed else self.due_at)

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

    COMPLETE = "complete"  # This repetition is done, but the chore is still active and will spawn alarms.
    SNOOZE = "snooze"
    JUMP = "jump"
    PAUSE = "pause"  # The chore is finished, no more alarms will be created.


ALARM_ACTION_ENUM = postgresql.ENUM(
    AlarmAction.COMPLETE, AlarmAction.SNOOZE, AlarmAction.JUMP, AlarmAction.PAUSE, name="alarm_action_enum"
)


class Alarm(SurrogatePK, CreatedUpdatedMixin, Model):
    """History of alarms from a chore."""

    __tablename__ = "alarm"

    chore_id = reference_col("chore")
    chore = db.relationship("Chore")
    """:type: dontforget.models.Chore"""

    action = db.Column(ALARM_ACTION_ENUM, nullable=False)
    due_at = db.Column(db.TIMESTAMP(timezone=True))
    alarm_at = db.Column(db.TIMESTAMP(timezone=True))
    snooze_repetition = db.Column(db.String())

    def __repr__(self):
        """Represent the alarm as a unique string."""
        return "<Alarm {!r} {!r} at '{}' (chore {!r})>".format(self.id, self.action, self.due_at, self.chore_id)
