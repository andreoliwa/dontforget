"""Create a task when it's time to go home."""
from datetime import date, timedelta
from pprint import pprint
from typing import Union

import arrow
from simple_settings import settings
from tapioca_toggl import Toggl

from dontforget.todoist import Todoist


def go_home(desired_date: Union[date, str, None] = None):
    """Determine the time to go home on the desired day."""
    api = Toggl(access_token=settings.TOGGL_API_TOKEN)
    my_data = api.me_with_related_data().get().data
    timezone = my_data.timezone().data

    if not desired_date:
        desired_date = arrow.now(timezone)
    day_start = arrow.get(desired_date).to(timezone).replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start.replace(hour=23, minute=59, second=59)

    entries = api.time_entries().get(params={"start_date": day_start, "end_date": day_end})

    # Find entries from projects which belong to the configured clients.
    toggl_clients = settings.go_home["toggl_clients"]
    print(f"Toggl clients: {', '.join(toggl_clients)}")
    client_ids = [client["id"] for client in my_data.clients().data if client["name"] in toggl_clients]
    client_projects = [project["id"] for project in my_data.projects().data if project["cid"] in client_ids]

    start_dates = [entry["start"] for entry in entries().data if entry["pid"] in client_projects]
    if not start_dates:
        print(f"No Toggl entries for {', '.join(toggl_clients)} in {desired_date.date().isoformat()}")
        return

    # Add 8 hours to the first entry.
    arrived_at = arrow.get(min(start_dates)).to(timezone)
    print(f"Arrived at work at {arrived_at}")
    go_home_at = (
        arrived_at + timedelta(hours=settings.go_home["hours"]) - timedelta(minutes=settings.go_home["minutes_before"])
    )

    # Find entries with tags and descriptions that should be added to the time to go home (e.g.: pause, not work)
    non_working_durations = [
        entry["duration"]
        for entry in entries().data
        for tag in settings.go_home["toggl_not_work_tags"]
        for desc in settings.go_home["toggl_not_work_descriptions"]
        if tag in entry.get("tags", []) or desc in entry.get("description", [])
    ]
    non_working_time = timedelta(seconds=sum(non_working_durations))
    print(f"Non working time: {non_working_time}")
    go_home_at += non_working_time
    print(f"Go home at {go_home_at}")

    todoist = Todoist()
    project_id = todoist.fetch_first("projects", "id", {"name": settings.go_home["todoist_project"]})
    if not project_id:
        print("No project ID")
        return

    task_description = settings.go_home["todoist_task"]
    date_string = f"{go_home_at.format('MMM DD, YYYY')} at {go_home_at.format('HH:mm')}"

    existing_task = todoist.fetch_first("items", None, {"project_id": project_id, "content": task_description})
    if not existing_task:
        # Create a new task
        item = todoist.api.items.add(
            task_description, project_id, date_string=date_string, priority=4, auto_reminder=True
        )
        todoist.api.commit()
        print("Task created")
    else:
        # Update existing task
        item = todoist.api.items.get_by_id(existing_task["id"])
        item.update(content=task_description, date_string=date_string, priority=4)
        todoist.api.commit()
        print("Task updated")
    pprint(item)
