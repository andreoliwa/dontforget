"""Create a task when it's time to go home."""

from datetime import date, timedelta
from typing import Union

import arrow
from simple_settings import settings
from tapioca_toggl import Toggl


def go_home(desired_date: Union[date, str, None]):
    """Determine the time to go home on the desired day."""
    if not desired_date:
        desired_date = arrow.now()
    day_start = arrow.get(desired_date).replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start.replace(hour=23, minute=59, second=59)

    api = Toggl(access_token=settings.TOGGL_API_TOKEN)
    my_data = api.me_with_related_data().get().data
    entries = api.time_entries().get(params={'start_date': day_start, 'end_date': day_end})

    # Find entries from projects which belong to the configured clients.
    client_ids = [client.id().data for client in my_data.clients
                  if client.name().data in settings.go_home['clients']]
    project_ids = [project.id().data for project in my_data.projects if project.cid().data in client_ids]
    selected_entries = [entry.start().data for entry in entries if entry.pid().data in project_ids]
    if not selected_entries:
        return

    # Add 8 hours to the first entry.
    first_entry_start = arrow.get(min(selected_entries))
    time_to_go_home = first_entry_start + timedelta(hours=settings.go_home['hours'])
    assert time_to_go_home  # FIXME:
