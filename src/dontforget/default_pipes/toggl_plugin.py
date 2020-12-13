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
import sys
from dataclasses import dataclass
from typing import Dict, Optional

import click
import keyring
from clib.files import fzf
from rumps import MenuItem
from toggl.TogglPy import Toggl

from dontforget.app import DontForgetApp
from dontforget.plugins.base import BasePlugin
from dontforget.settings import LOG_LEVEL, load_config_file

KEYRING_API_TOKEN = "api_token"

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


class TogglPlugin(BasePlugin):
    """Toggl plugin."""

    toggl = Toggl()
    entries: Dict[str, TogglEntry] = {}
    menu_items: Dict[str, TogglMenuItem] = {}

    @property
    def name(self) -> str:
        """Plugin name."""
        return "Toggl"

    def init_app(self, app: DontForgetApp) -> bool:
        """Init the plugin."""
        self.app = app
        if not self.set_api_token():
            return False
        return self.create_menu()

    def set_api_token(self):
        """Set the API token to communicate with the Toggl API."""
        api_token = keyring.get_password(self.name, KEYRING_API_TOKEN)
        if not api_token:
            message = (
                "The Toggl API token is not set on the keyring."
                f" Run this command and paste the token: keyring set {self.name} {KEYRING_API_TOKEN}"
            )
            logger.error(message)
            click.secho(message, fg="bright_red")
            return False
        self.toggl.setAPIKey(api_token)
        return True

    def create_menu(self) -> bool:
        """Create menu items.

        Read items in reversed order because they will be added to the menu always after the main menu.
        """
        self.fetch_entries()

        for entry in self.entries.values():  # type: TogglEntry
            menu_key = f"{entry.name} ({entry.client}/{entry.project})"
            menuitem = TogglMenuItem(menu_key, callback=self.entry_clicked)
            menuitem.entry = entry
            menuitem.updated = True
            self.app.menu.insert_after(self.name, menuitem)
            self.menu_items[menu_key] = menuitem
        return True

    def fetch_entries(self) -> Dict[str, TogglEntry]:
        """Fetch client and projects from Toggl entries."""
        self.entries = {}
        for data in reversed(self.plugin_config):
            entry = TogglEntry(**data)
            logger.debug("Fetching client/project for Toggl entry: %s", entry)

            # TODO: this method is completely not optimized; it makes lots of requests and there is no cache
            project_data = self.toggl.getClientProject(entry.client, entry.project)
            entry.project_id = project_data["data"]["id"]
            entry.client_id = project_data["data"]["cid"]
            self.entries[entry.name] = entry
        return self.entries

    def reload_config(self) -> bool:
        """Replace menus when the configuration is reloaded."""
        for menu in self.menu_items.values():
            menu.updated = False

        rv = self.create_menu()

        # Remove menu items that were not updated
        old_menus = self.menu_items.copy()
        self.menu_items.clear()
        for key, menu in old_menus.items():
            if menu.updated:
                self.menu_items[key] = menu
            else:
                del self.app.menu[key]

        return rv

    def entry_clicked(self, menu: TogglMenuItem):
        """Callback executed when a menu entry is clicked."""
        self.track_entry(menu.entry)

    @classmethod
    def register_cli_commands(cls):
        """Register CLI commands for this plugin."""
        return [track]

    def track_entry(self, entry: TogglEntry, echo=False):
        """Track an entry on Toggl."""
        msg = f"Starting Toggl entry: {entry.name}"
        if echo:
            click.echo(msg)
        logger.debug(msg)
        self.toggl.startTimeEntry(entry.name, self.entries[entry.name].project_id)


@click.command()
@click.argument("entry", nargs=-1, required=True)
def track(entry):
    """Track your work with Toggl."""
    joined_text = "".join(entry)

    config_yaml = load_config_file()
    plugin = TogglPlugin(config_yaml)
    if not plugin.set_api_token():
        sys.exit(-1)
    entries = plugin.fetch_entries()
    chosen = fzf(list(entries.keys()), query=joined_text)
    if not chosen:
        return
    entry = plugin.entries[chosen]
    plugin.track_entry(entry, True)
