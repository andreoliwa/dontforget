"""Toggl plugin.

Following suggestions from https://github.com/toggl/toggl_api_docs#python:

https://github.com/AuHau/toggl-cli is a no-go, I'm really annoyed by many failed attempts.
For starters, it doesn't work with `poetry`: https://github.com/python-poetry/poetry/issues/2372
I tried installing it manually with `pip`, then `poetry install`.
Why is it loading the CLI if I'm using the API wrapper?

File "~/Library/Caches/pypoetry/virtualenvs/dontforget-KBL7kC6p-py3.7/lib/python3.7/site-packages/toggl/cli/commands.py", line 49, in <module>
    @click.group(cls=utils.SubCommandsGroup)
AttributeError: module 'toggl.utils' has no attribute 'SubCommandsGroup'
"""
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import click
import keyring
from rumps import MenuItem
from toggl.TogglPy import Toggl

from dontforget.app import DontForgetApp
from dontforget.settings import LOG_LEVEL

API_TOKEN = "api_token"

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)


@dataclass
class TogglEntry:
    """An entry on Toggl."""

    name: str
    client: Optional[str] = None
    client_id: Optional[int] = None
    project: Optional[str] = None
    project_id: Optional[int] = None


class TogglMenuItem(MenuItem):
    """A Toggl menu item."""

    entry: TogglEntry
    updated: bool = True


class TogglPlugin:
    """Toggl plugin."""

    name = "Toggl"

    def __init__(self, app: DontForgetApp) -> None:
        self.app = app
        self.toggl = Toggl()
        self.entries: Dict[str, TogglEntry] = {}
        self.menu_items: Dict[str, TogglMenuItem] = {}

    def init_app(self, config_list: List[dict]) -> bool:
        """Init the plugin."""
        api_token = keyring.get_password(self.name, API_TOKEN)
        if not api_token:
            message = (
                "The Toggl API token is not set on the keyring."
                f" Run this command and paste the token: poetry run keyring set {self.name} {API_TOKEN}"
            )
            logger.error(message)
            click.secho(message, fg="bright_red")
            return False
        self.toggl.setAPIKey(api_token)

        return self.create_menu(config_list)

    def create_menu(self, config_list: List[dict]) -> bool:
        """Create menu items.

        Read items in reversed order because they will be added to the menu always after the main menu.
        """
        for data in reversed(config_list):
            entry = TogglEntry(**data)
            logger.debug("Toggl entry: %s", entry)

            # TODO: this method is completely not optimized; it makes lots of requests and there is no cache
            project_data = self.toggl.getClientProject(entry.client, entry.project)
            entry.project_id = project_data["data"]["id"]
            entry.client_id = project_data["data"]["cid"]

            menu_key = f"{entry.name} ({entry.client}/{entry.project})"
            menuitem = TogglMenuItem(menu_key, callback=self.start_entry)
            menuitem.entry = entry
            menuitem.updated = True
            self.app.menu.insert_after(self.name, menuitem)

            self.entries[entry.name] = entry
            self.menu_items[menu_key] = menuitem
        return True

    def reload_config(self, config_list: List[dict]) -> bool:
        """Replace menus when the configuration is reloaded."""
        self.entries = {}
        for menu in self.menu_items.values():
            menu.updated = False

        rv = self.create_menu(config_list)

        # Remove menu items that were not updated
        old_menus = self.menu_items.copy()
        self.menu_items.clear()
        for key, menu in old_menus.items():
            if menu.updated:
                self.menu_items[key] = menu
            else:
                del self.app.menu[key]

        return rv

    def start_entry(self, menu: TogglMenuItem):
        """Callback executed when a menu entry is clicked."""
        logger.debug("Starting Toggl entry: %s", menu.entry.name)
        self.toggl.startTimeEntry(menu.entry.name, self.entries[menu.entry.name].project_id)
