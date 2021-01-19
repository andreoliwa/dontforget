"""Toggl plugin.

Followed some suggestions from https://github.com/toggl/toggl_api_docs#python.
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Union

import click
import keyring
import maya
import vcr
from clib.files import fzf
from click import ClickException
from joblib import Memory
from rumps import MenuItem
from toggl import api
from vcr.persisters.filesystem import FilesystemPersister

from dontforget.app import DontForgetApp
from dontforget.plugins.base import BasePlugin
from dontforget.settings import DEFAULT_DIRS, LOG_LEVEL, load_config_file

KEYRING_API_TOKEN = "api_token"
CACHE_DIR = Path(DEFAULT_DIRS.user_cache_dir)
CACHE_EXPIRATION_SECONDS = 60 * 60

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

my_vcr = vcr.VCR()
memory = Memory(CACHE_DIR, verbose=0)


class ExpiredCassettePersister(FilesystemPersister):
    """Expired cassette persister."""

    @classmethod
    def load_cassette(cls, cassette_path, serializer):
        """Load the cassette if it's within the expected TTL."""
        path = Path(cassette_path)
        if path.exists():
            file_stat = path.stat()
            delta = datetime.now() - datetime.fromtimestamp(file_stat.st_mtime)
            if delta.total_seconds() > CACHE_EXPIRATION_SECONDS:
                raise ValueError("TTL expired, recreating the cassette")
        return super().load_cassette(cassette_path, serializer)

    @classmethod
    def save_cassette(cls, cassette_path, cassette_dict, serializer):
        """Save the cassette."""
        super().save_cassette(cassette_path, cassette_dict, serializer)


my_vcr.register_persister(ExpiredCassettePersister)


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


ClientStore = Dict[Union[int, str], ClientDC]


@dataclass
class ProjectDC:
    """A project on Toggl."""

    id: int
    name: str
    client: ClientDC


ProjectStore = Dict[Union[int, str], ProjectDC]


class TogglMenuItem(MenuItem):
    """A Toggl menu item."""

    entry: ShortcutDC
    updated: bool = True


@memory.cache
def fetch_all_clients() -> ClientStore:
    """Cache all Toggl clients."""
    rv = {c.id: ClientDC(c.id, c.name) for c in api.Client.objects.all()}
    rv.update({value.name: value for key, value in rv.items()})
    return rv


@memory.cache
def fetch_all_projects() -> ProjectStore:
    """Cache all Toggl projects."""
    all_clients = fetch_all_clients()
    rv = {p.id: ProjectDC(p.id, p.name, all_clients[p.cid]) for p in api.Project.objects.all()}
    rv.update({value.name: value for key, value in rv.items()})
    return rv


class TogglPlugin(BasePlugin):
    """Toggl plugin."""

    shortcuts: Dict[str, ShortcutDC] = {}
    menu_items: Dict[str, TogglMenuItem] = {}
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
        api_token = keyring.get_password(self.name, KEYRING_API_TOKEN)
        if not api_token:
            message = (
                "The Toggl API token is not set on the keyring."
                f" Run this command and paste the token: keyring set {self.name} {KEYRING_API_TOKEN}"
            )
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

    def fetch_shortcuts(self) -> Dict[str, ShortcutDC]:
        """Fetch client and projects from Toggl shortcuts."""
        self.shortcuts: Dict[str, ShortcutDC] = {}
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
        # FIXME[AA]:
        # self.toggl.startTimeEntry(entry.name, self.shortcuts[entry.name].project_id)


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

    exclude_project_names = report_config["exclude_projects"]
    chosen_project_ids = {
        project.id
        for project in plugin.project_store.values()
        if project.client.id in chosen_client_ids and project.name not in exclude_project_names
    }

    start_date = maya.when(date).datetime()
    lines = set()
    for entry in api.TimeEntry.objects.filter(start=start_date):
        if entry.pid not in chosen_project_ids:
            continue
        lines.add(f"- {plugin.project_store[entry.pid].name}: {entry.description}")

    for line in sorted(lines):
        click.echo(line)
