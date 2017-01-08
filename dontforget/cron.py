# -*- coding: utf-8 -*-
"""Functions meant to be called several times, manually or with cron jobs."""
from datetime import datetime

from sqlalchemy.sql import func

from dontforget.extensions import db
from dontforget.models import Alarm, AlarmState, Chore
from dontforget.repetition import next_dates


def spawn_alarms(right_now=None):
    """Spawn alarms for active chores which don't have unseen alarms.

    :param datetime right_now: Desired date/time. If none, assumes the current date/time.
    :return: Number of alarms created.
    :rtype: int
    """
    # pylint: disable=no-member
    query = db.session.query(
        Chore.id, Chore.alarm_start, Chore.repetition, Chore.repeat_from_completed,
        Alarm.current_state, Alarm.updated_at, func.max(Alarm.next_at)
    ).outerjoin(Alarm, Chore.id == Alarm.chore_id).group_by(Chore.id).filter(Chore.active_expression(right_now))

    alarms_created = 0
    for chore_id, alarm_start, repetition, repeat_from_completed, current_state, updated_at, last_alarm in query.all():
        next_at = None
        # It's a new chore; let's create the first alarm with the chore alarm start.
        if current_state is None:
            next_at = alarm_start
        # If the chore has a repetition and the last alarm is completed, create a new alarm.
        # If the chore has no repetition, skip alarm creation.
        elif repetition and current_state == AlarmState.COMPLETED:
            # The next alarm date depends on the chore: it can be from the completed date or from the last alarm date.
            reference_date = updated_at if repeat_from_completed else last_alarm
            next_at = next_dates(repetition, reference_date)

        if next_at is not None:
            Alarm.create_unseen(chore_id, next_at)
            alarms_created += 1
    if alarms_created:
        db.session.commit()
    return alarms_created


def display_unseen_alarms(right_now=None):
    """Display unseen alarms from the past (before right now), and change their state to displayed.

    :return: Number of alarms displayed.
    :rtype: int
    """
    # The module must be imported here, for the mock.patch to work on the tests;
    # otherwise the module is loaded before its time.
    from dontforget.ui import show_dialog

    if not right_now:
        right_now = datetime.utcnow()

    count = 0
    # pylint: disable=no-member
    query = Alarm.query.filter(Alarm.current_state == AlarmState.UNSEEN,
                               Alarm.next_at <= right_now).order_by(Alarm.id)
    for unseen_alarm in query.all():
        unseen_alarm.current_state = AlarmState.DISPLAYED
        db.session.add(unseen_alarm)

        show_dialog(unseen_alarm)
        count += 1
    if count:
        db.session.commit()
    return count
