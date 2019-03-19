"""Todoist API interface.

Docs: https://developer.todoist.com/sync/v7/
Python module: https://github.com/Doist/todoist-python
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from marshmallow import Schema, ValidationError, fields
from todoist import TodoistAPI

from dontforget.config import TODOIST_API_TOKEN
from dontforget.target import BaseTarget
from dontforget.types import JsonDict


class Todoist:
    """A wrapper for the Todoist API."""

    def __init__(self):
        self.api = TodoistAPI(TODOIST_API_TOKEN)
        self.response: Dict[str, Any] = {}

    def sync(self):
        """Login if needed, then sync."""
        self.response = self.api.sync()

    def clear(self):
        """Reset the state to perform a new sync."""
        self.api.reset_state()

    def keys(self):
        """Keys of the response."""
        return sorted(self.response.keys())

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
        # TODO: accept multiple return_fields
        # TODO: use jmespath to search the JSON?
        if not filters:
            values_to_list: JsonDict = {}
        else:
            values_to_list = {key: [value] if not isinstance(value, list) else value for key, value in filters.items()}
        found_elements = [
            element[return_field] if return_field else element
            for element in self.response[element_name]
            if not filters or matching_function(element[key] in value for key, value in values_to_list.items())
        ]
        if index is not None:
            return found_elements[index] if found_elements else None
        return found_elements

    def fetch_first(self, element_name: str, return_field: str = None, filters: JsonDict = None) -> Optional[Any]:
        """Fetch only the first result from the fetched list, or None if the list is empty."""
        return self.fetch(element_name, return_field, filters, 0)

    def fetch_project_id_by(self, exact_name: str) -> Optional[int]:
        """Fetch a project ID by its exact name."""
        return self.fetch_first("projects", "id", {"name": exact_name})

    def fetch_project_items(self, exact_name: str, return_field: str = None) -> List[JsonDict]:
        """Fetch all project items."""
        project_id = self.fetch_project_id_by(exact_name)
        if not project_id:
            return []
        return self.fetch("items", return_field, {"project_id": project_id})

    def find_first_item(self, project_exact_name: str, item_partial_content: str) -> Optional[JsonDict]:
        """Return the first item on a project by its partial content."""
        lower_item_partial_content = item_partial_content.lower()
        for item in self.fetch_project_items(project_exact_name):
            if lower_item_partial_content in item.get("content", "").lower():
                return item
        return None


class TodoistSchema(Schema):
    """Task schema."""

    project: str = fields.String()
    project_id: int = fields.Integer()
    content: str = fields.String()
    comment: str = fields.String()
    due: datetime = fields.DateTime()
    priority: int = fields.Integer()


class TodoistTarget(BaseTarget):
    """Add a task to Todoist."""

    def __init__(self, raw_data: Dict[str, Any]):
        super().__init__(raw_data)
        self.todoist = Todoist()

    def process(self) -> bool:
        """Add a task to Todoist."""
        schema = TodoistSchema(strict=True)
        try:
            self.valid_data, _ = schema.load(self.raw_data)
        except ValidationError as err:
            self.validation_error = err
            return False

        self.todoist.clear()
        self.todoist.sync()
        self.set_project_id()
        self.add_task()
        return True

    def set_project_id(self):
        """Set the project ID from the project name."""
        project = self.valid_data["project"]
        project_id = self.todoist.fetch_first("projects", "id", {"name": project})
        if project_id:
            self.valid_data["project_id"] = project_id

    def add_task(self):
        """Add a task to Todoist from the valid data."""
        content = self.valid_data.pop("content", "")
        self.todoist.api.add_item(content, **self.valid_data)
