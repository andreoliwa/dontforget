"""Redmine."""
from pprint import pprint

from redminelib import Redmine

from dontforget.pipes import BaseSource


class RedmineSource(BaseSource):
    """Redmine source."""

    pass


if __name__ == "__main__":
    from environs import Env

    env = Env()
    env.read_env()

    redmine = Redmine(env("REDMINE_URL"), key=env("REDMINE_API_TOKEN"), raise_attr_exception=False)
    project = redmine.project.get("vila-mariana")
    pprint(list(redmine.issue_status.all().values("id", "name")))
    pprint(list(project.issues.values("id", "subject", "due_date")))
