# -*- coding: utf-8 -*-
"""Functions meant to be called several times, manually or with cron jobs."""
from sqlalchemy import and_
from sqlalchemy.sql import func

from dontforget.app import db
from dontforget.models import Alarm, AlarmState, Chore
from dontforget.repetition import next_dates


def spawn_alarms():
    """Spawn alarms for active chores which don't have unseen alarms.

    :return: Number of alarms created.
    :rtype: int
    """
    # pylint: disable=no-member
    result = db.session.query(Chore.id, func.max(Alarm.next_at).label('max_next_at')).outerjoin(Alarm).filter(
        Chore.active_expression()).group_by(Chore.id).subquery()

    query = db.session.query(
        Chore.id, Chore.alarm_start, Chore.repetition, Chore.repeat_from_completed,
        Alarm.current_state, Alarm.updated_at, Alarm.next_at
    ).join(result, result.c.id == Chore.id).outerjoin(
        Alarm, and_(Chore.id == Alarm.chore_id, result.c.max_next_at == Alarm.next_at)).order_by(Chore.id)

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
