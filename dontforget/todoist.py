"""Todoist API interface.

Docs: https://developer.todoist.com/sync/v7/
Python module: https://github.com/Doist/todoist-python
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

import click
import jmespath
from deprecated import deprecated
from marshmallow import Schema, ValidationError, fields
from todoist import TodoistAPI

from dontforget.generic import SingletonMixin
from dontforget.pipes import BaseTarget
from dontforget.typedefs import JsonDict

PROJECTS_NAME_ID_JMEX = jmespath.compile("projects[*].[name,id]")
DictProjectId = Dict[str, int]


class Todoist(SingletonMixin):
    """A wrapper for the Todoist API."""

    def __init__(self, api_token: str) -> None:
        super().__init__()
        self.api = TodoistAPI(api_token)
        self.data: JsonDict = {}
        self.projects: DictProjectId = {}
        self._allow_creation = False

    def smart_sync(self):
        """Only perform a full resync if needed."""
        if not self.data.get("projects", {}):
            # If internal data has no projects, reset the state and a full (slow) sync will be performed.
            self.api.reset_state()

        partial_data = self.api.sync()
        self._merge_new_data(partial_data)

        self.projects = dict(PROJECTS_NAME_ID_JMEX.search(self.data))

    def _merge_new_data(self, partial_data: JsonDict):
        if not self.data:
            self.data = partial_data
            return

        for key, value in partial_data.items():
            if isinstance(value, list):
                if key not in self.data:
                    self.data[key] = []
                self.data[key].extend(value)
            elif isinstance(value, dict):
                if key not in self.data:
                    self.data[key] = {}
                self.data[key].update(value)
            else:
                self.data[key] = value

    def keys(self):
        """Keys of the data."""
        return sorted(self.data.keys())

    @deprecated(reason="use find* functions instead")
    def fetch(
        self,
        element_name: str,
        return_field: str = None,
        filters: JsonDict = None,
        index: int = None,
        matching_function=all,
    ) -> List[Any]:
        """Fetch elements matching items that satisfy the desired parameters.

        :param element_name: Name of the element to search. E.g. 'projects', 'items'.
        :param return_field: Name of the return field. If None, return the whole element.
        :param filters: Parameters for the search.
        :param index: Desired index to be returned. If nothing was found, return None.
        :param matching_function: ``all`` items by default, but ``any`` can be used as well.
        """
        if not filters:
            values_to_list: JsonDict = {}
        else:
            values_to_list = {key: [value] if not isinstance(value, list) else value for key, value in filters.items()}
        found_elements = [
            element[return_field] if return_field else element
            for element in self.data[element_name]
            if not filters or matching_function(element[key] in value for key, value in values_to_list.items())
        ]
        if index is not None:
            return found_elements[index] if found_elements else None
        return found_elements

    @deprecated(reason="use find* functions instead")
    def fetch_first(self, element_name: str, return_field: str = None, filters: JsonDict = None) -> Optional[Any]:
        """Fetch only the first result from the fetched list, or None if the list is empty."""
        return self.fetch(element_name, return_field, filters, 0)

    def find_project_id(self, exact_name: str) -> Optional[int]:
        """Find a project ID by its exact name.

        :param exact_name: Exact name of a project.
        """
        return self.projects.get(exact_name, None)

    def find_projects(self, partial_name: str = "") -> DictProjectId:
        """Find projects by partial name.

        :param partial_name: Partial name of a project.
        """
        return {
            name: project_id for name, project_id in self.projects.items() if partial_name.casefold() in name.casefold()
        }

    def find_project_items(self, exact_project_name: str, extra_jmes_expression: str = "") -> List[JsonDict]:
        """Fetch all project items by the exact project name.

        :param exact_project_name: Exact name of a project.
        :param extra_jmes_expression: Extra JMESPath expression to filter fields, for instance.
        """
        project_id = self.find_project_id(exact_project_name)
        if not project_id:
            return []
        return jmespath.search(f"items[?project_id==`{project_id}`]{extra_jmes_expression}", self.data)

    def find_items_by_content(self, exact_project_name: str, partial_content: str) -> List[JsonDict]:
        """Return items of a project by partial content.

        :param exact_project_name: Exact name of a project.
        :param partial_content: Partial content of an item.
        """
        clean_content = partial_content.casefold()
        return [
            item
            for item in self.find_project_items(exact_project_name)
            if clean_content in item.get("content", "").casefold()
        ]


class TodoistSchema(Schema):
    """Task schema."""

    #: Unique ID for the task, determined by the caller.
    id: str = fields.String(required=True)
    url: str = fields.Url(required=True)
    content: str = fields.String(required=True)
    project: str = fields.String()
    project_id: int = fields.Integer()
    comment: str = fields.String()
    date_string: datetime = fields.DateTime(format="rfc")
    priority: int = fields.Integer()


class TodoistTarget(BaseTarget):
    """Add a task to Todoist."""

    todoist: Todoist

    def push(self, raw_data: JsonDict) -> bool:
        """Add a task to Todoist."""
        schema = TodoistSchema(strict=True)
        try:
            self.valid_data, _ = schema.load(raw_data)
            self.serialised_data, _ = schema.dump(self.valid_data)
            click.echo(f" {self.serialised_data}...", nl=False)
        except ValidationError as err:
            self.validation_error = str(err)
            return False

        self.todoist = Todoist.singleton(raw_data["api_token"])
        self.todoist.smart_sync()
        self._set_project_id()
        if self.todoist.find_items_by_content(self.serialised_data["project"], self.unique_key):
            self.validation_error = "Task already exists"
            return False

        self._add_task()
        return True

    def _set_project_id(self):
        """Set the project ID from the project name."""
        project_id = self.todoist.find_project_id(self.serialised_data["project"])
        if project_id:
            self.serialised_data["project_id"] = project_id

    def _add_task(self):
        """Add a task to Todoist from the valid data."""
        content = self.serialised_data.pop("content", "")
        url = self.serialised_data.pop("url", "")
        self.todoist.api.add_item(f"[{content} {self.unique_key}]({url})", **self.serialised_data)
