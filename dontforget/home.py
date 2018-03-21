"""Create a task when it's time to go home."""

from datetime import date, timedelta
from typing import Union

import arrow
from simple_settings import settings
from tapioca_toggl import Toggl

from dontforget.todoist import Todoist


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
                  if client.name().data in settings.go_home['toggl_clients']]
    client_projects = [project.id().data for project in my_data.projects if project.cid().data in client_ids]
    start_dates = [entry.start().data for entry in entries if entry.pid().data in client_projects]
    if not start_dates:
        return

    # Add 8 hours to the first entry.
    first_start_date = arrow.get(min(start_dates))
    time_to_go_home = first_start_date + timedelta(hours=settings.go_home['hours'])

    # Find entries from projects that should be added to the time to go home.
    add_projects = [project.id().data for project in my_data.projects
                    if project.name().data in settings.go_home['toggl_add_projects']]
    add_entries = [entry.duration().data for entry in entries if entry.pid().data in add_projects]
    if not add_entries:
        return

    time_to_go_home += timedelta(seconds=sum(add_entries))

    todoist = Todoist()
    project_id = todoist.fetch_first('projects', 'id', {'name': settings.go_home['todoist_project']})
    if not project_id:
        return

    task = todoist.fetch_first('items', 'content',
                               {'project_id': project_id, 'content': settings.go_home['todoist_task']})
    print(task)  # FIXME:
