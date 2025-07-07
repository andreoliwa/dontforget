"""Toggl plugin.

* https://github.com/toggl/toggl_api_docs#python
* https://github.com/AuHau/toggl-cli/blob/master/toggl/api/models.py
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Union

import click
import maya
from clib.files import fzf
from click import ClickException
from rumps import MenuItem
from toggl import api

from dontforget.app import BasePlugin, DontForgetApp
from dontforget.settings import JOBLIB_MEMORY, LOG_LEVEL, TOGGL_API_TOKEN, load_config_file

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)


@dataclass
class ShortcutDC:
    """An entry on Toggl."""

    name: str
    client: str
    project: str
    client_id: Optional[int] = None
    project_id: Optional[int] = None


@dataclass
class ClientDC:
    """A client on Toggl."""

    id: int
    name: str


ClientStore = dict[Union[int, str], ClientDC]


@dataclass
class ProjectDC:
    """A project on Toggl."""

    id: int
    name: str
    client: ClientDC


ProjectStore = dict[Union[int, str], ProjectDC]


class TogglMenuItem(MenuItem):
    """A Toggl menu item."""

    entry: ShortcutDC
    updated: bool = True


@JOBLIB_MEMORY.cache
def fetch_all_clients() -> ClientStore:
    """Cache all Toggl clients."""
    rv = {c.id: ClientDC(c.id, c.name) for c in api.Client.objects.all()}
    rv.update({value.name: value for key, value in rv.items()})
    return rv


@JOBLIB_MEMORY.cache
def fetch_all_projects() -> ProjectStore:
    """Cache all Toggl projects."""
    all_clients = fetch_all_clients()
    rv = {}
    for p in api.Project.objects.all():
        if p.client_id not in all_clients:
            # Probably an archived project with entries
            continue

        proj = ProjectDC(p.id, p.name, all_clients[p.client_id])
        click.echo(f"Project: {p} Client: {p.client} - {proj}")
        rv[p.id] = proj
    rv.update({value.name: value for key, value in rv.items()})
    return rv


class TogglPlugin(BasePlugin):
    """Toggl plugin."""

    shortcuts: dict[str, ShortcutDC] = {}
    menu_items: dict[str, TogglMenuItem] = {}
    client_store: ClientStore = {}
    project_store: ProjectStore = {}

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

    @classmethod
    def create(cls) -> "TogglPlugin":
        """Plugin factory."""
        return cls(load_config_file())

    def set_api_token(self):
        """Set the API token to communicate with the Toggl API."""
        api_token = TOGGL_API_TOKEN
        if not api_token:
            message = "The Toggl API token is not set on the environment variable TOGGL_API_TOKEN."
            logger.error(message)
            click.secho(message, fg="bright_red")
            return False
        return True

    def create_menu(self) -> bool:
        """Create menu items.

        Read items in reversed order because they will be added to the menu always after the main menu.
        """
        self.fetch_shortcuts()

        for shortcut in self.shortcuts.values():  # type: ShortcutDC
            menu_key = f"{shortcut.name} ({shortcut.client}/{shortcut.project})"
            menuitem = TogglMenuItem(menu_key, callback=self.entry_clicked)
            menuitem.entry = shortcut
            menuitem.updated = True
            self.app.menu.insert_after(self.name, menuitem)
            self.menu_items[menu_key] = menuitem
        return True

    def fetch_shortcuts(self) -> dict[str, ShortcutDC]:
        """Fetch client and projects from Toggl shortcuts."""
        self.shortcuts: dict[str, ShortcutDC] = {}
        self.fetch_clients_projects()

        for data in reversed(self.plugin_config["shortcuts"]):
            shortcut = ShortcutDC(**data)
            logger.debug("Fetching client/project for Toggl entry: %s", shortcut)

            shortcut.project_id = self.project_store[shortcut.project].id
            shortcut.client_id = self.client_store[shortcut.client].id
            self.shortcuts[shortcut.name] = shortcut
        return self.shortcuts

    def fetch_clients_projects(self) -> "TogglPlugin":
        """Fetch all clients and projects."""
        self.client_store = fetch_all_clients()
        self.project_store = fetch_all_projects()
        return self

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
        return [track, what_i_did]

    def track_entry(self, entry: ShortcutDC, echo=False):
        """Track an entry on Toggl."""
        msg = f"Starting Toggl entry: {entry.name}"
        if echo:
            click.echo(msg)
        logger.debug(msg)
        api.TimeEntry.start_and_save(description=entry.name, project=self.shortcuts[entry.name].project_id)


@click.command()
@click.argument("entry", nargs=-1)
def track(entry):
    """Track your work with Toggl."""
    joined_text = "".join(entry).strip().lower()

    plugin = TogglPlugin.create()
    shortcuts = plugin.fetch_shortcuts()
    chosen = fzf(list(shortcuts.keys()), query=joined_text)
    if not chosen:
        raise ClickException("No entry chosen")

    shortcut = plugin.shortcuts[chosen]
    plugin.track_entry(shortcut, True)


@click.command()
@click.argument("date", nargs=1)
@click.argument("report", nargs=1)
def what_i_did(date, report):
    """Display a report of what I did on Toggl since the chosen date."""
    plugin = TogglPlugin.create().fetch_clients_projects()

    report_config = plugin.plugin_config["what_i_did"][report]
    expected_client_names = set(report_config["clients"])
    chosen_client_ids = {client.id for client in plugin.client_store.values() if client.name in expected_client_names}
    order_by = report_config.get("order_by", [])

    exclude_project_names = report_config["exclude_projects"]
    chosen_project_ids = {
        project.id
        for project in plugin.project_store.values()
        if project.client.id in chosen_client_ids and project.name not in exclude_project_names
    }

    start_date = maya.when(date).datetime()
    end_date = datetime.now()
    lines = set()
    filtered_entries = api.TimeEntry.objects.all(start_date=start_date, end_date=end_date)

    # togglCli, Toggl API and Maya have bugs at the moment, so let's log always
    logger.warning(
        "Start date '%s' parsed by Maya: %s / End date: %s / Filtered entries: %s / Chosen projects: %s",
        date,
        start_date,
        end_date,
        len(filtered_entries),
        len(chosen_project_ids),
    )
    for entry in filtered_entries:
        logger.debug("Entry: %s", entry)
        # TODO: The start_date and end_date filters are not working; all recent entries are being returned
        if entry.start < start_date:
            continue
        try:
            if entry.project_id not in chosen_project_ids:
                continue
        except AttributeError:
            logger.error(f"This entry has no project: {entry}")
            continue
        lines.add(f"{plugin.project_store[entry.project_id].name}: {entry.description}")

    def sort_by_project(value: str):
        """Sort lines with a pre-defined order.

        If the value is not found on the ``order_by`` list, it goes to the top.
        """
        for project_index, project in enumerate(order_by):
            if value.startswith(project):
                return project_index
        return -1

    for line in sorted(lines, key=sort_by_project):
        click.echo(f"  - {line}")
