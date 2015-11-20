# -*- coding: utf-8 -*-
"""Functions meant to be called several times, manually or with cron jobs."""
from datetime import datetime

from sqlalchemy import and_, or_
from sqlalchemy.sql import func

from dontforget.extensions import db
from dontforget.models import Alarm, AlarmState, Chore
from dontforget.repetition import guess_from_str


def spawn_alarms(right_now=None):
    """Spawn alarms for active chores which don't have unseen alarms.

    :param datetime right_now: Desired date/time. If none, assumes the current date/time.
    :return: Number of alarms created.
    :rtype: int
    """
    if right_now is None:
        right_now = datetime.now()
    active_chores_now = and_(Chore.alarm_start <= right_now,
                             or_(right_now <= Chore.alarm_end, Chore.alarm_end.is_(None)))
    # pylint: disable=no-member
    query = db.session.query(
        Chore.id, Chore.alarm_start, Chore.repetition, Alarm.current_state, func.max(Alarm.next_at)
    ).outerjoin(Alarm, Chore.id == Alarm.chore_id).group_by(Chore.id).filter(active_chores_now)

    alarms_created = 0
    for chore_id, alarm_start, repetition, current_state, last_alarm in query.all():
        next_at = None
        if current_state is None:
            # It's a new chore; let's create the first alarm with the chore alarm start.
            next_at = alarm_start
        elif repetition and current_state == AlarmState.COMPLETED:
            # If the chore has a repetition and the last alarm is completed, create a new alarm.
            # If the chore has no repetition, skip alarm creation.
            next_at = guess_from_str(repetition).next_date(last_alarm)
            # TODO right_now if repeat_from_done else last_alarm

        if next_at is not None:
            alarm = Alarm(chore_id=chore_id, current_state=AlarmState.UNSEEN, next_at=next_at)
            db.session.add(alarm)
            alarms_created += 1
    if alarms_created:
        db.session.commit()
    return alarms_created


def display_unseen_alarms():
    """Display all unseen alarms in the database, and change their state to displayed.

    :return: Number of alarms displayed.
    :rtype: int
    """
    # The module must be imported here, for the mock.patch to work on the tests;
    # otherwise the module is loaded before its time.
    from dontforget.ui import show_dialog

    count = 0
    # pylint: disable=no-member
    query = Alarm.query.filter(Alarm.current_state == AlarmState.UNSEEN).order_by(Alarm.id)
    for unseen_alarm in query.all():
        unseen_alarm.current_state = AlarmState.DISPLAYED
        db.session.add(unseen_alarm)

        show_dialog(unseen_alarm)
        count += 1
    if count:
        db.session.commit()
    return count
