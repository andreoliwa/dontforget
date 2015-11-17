# -*- coding: utf-8 -*-
"""Functions meant to be called several times, manually or with cron jobs."""
from datetime import datetime

from sqlalchemy import and_, or_

from dontforget.extensions import db
from dontforget.models import Alarm, AlarmState, Chore


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
    query = Chore.query.outerjoin(
        Alarm, and_(Chore.id == Alarm.chore_id, Alarm.current_state == AlarmState.UNSEEN)) \
        .filter(active_chores_now, Alarm.chore_id.is_(None))
    alarms_created = 0
    for chore in query.all():
        alarm = Alarm(chore=chore, current_state=AlarmState.UNSEEN, next_at=chore.alarm_start)
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
