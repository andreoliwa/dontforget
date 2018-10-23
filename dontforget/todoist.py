"""Todoist API interface.

Docs: https://developer.todoist.com/sync/v7/
Python module: https://github.com/Doist/todoist-python
"""
from typing import Any, Dict, List, Union

from simple_settings import settings
from todoist import TodoistAPI


class Todoist:
    """A wrapper for the Todoist API."""

    def __init__(self):
        self.api = TodoistAPI()
        self.response = None

    def sync(self):
        """Login if needed, then sync."""
        if self.response:
            return
        self.api.user.login(settings.TODOIST_USER, settings.TODOIST_PASSWORD)
        self.response = self.api.sync()

    def fetch(
        self,
        element_name: str,
        return_field: Union[str, None],
        params: Dict[str, Union[str, List[str]]],
        index: Union[int, None] = None,
        matching_function=all,
    ) -> List[Any]:
        """Fetch elements matching items that satisfy the desired parameters.

        :param element_name: Name of the element to search. E.g. 'projects', 'items'.
        :param return_field: Name of the return field. If None, return the whole element.
        :param params: Parameters for the search.
        :param index: Desired index to be returned. If nothing was found, return None.
        :param matching_function: ``all`` items by default, but ``any`` can be used as well.
        """
        self.sync()
        values_to_list = {key: [value] if not isinstance(value, list) else value for key, value in params.items()}
        found_elements = [
            element[return_field] if return_field else element
            for element in self.response[element_name]
            if matching_function(element[key] in value for key, value in values_to_list.items())
        ]
        if index is not None:
            return found_elements[index] if found_elements else None
        return found_elements

    def fetch_first(
        self, element_name: str, return_field: str, params: Dict[str, Union[str, List[str]]]
    ) -> Union[Any, None]:
        """Fetch only the first result from the fetched list, or None if the list is empty."""
        return self.fetch(element_name, return_field, params, 0)
