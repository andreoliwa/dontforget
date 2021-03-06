"""GMail checker. It is not a source nor a target... yet.

Parts of the code below adapted from:
https://github.com/gsuitedevs/python-samples/blob/master/gmail/quickstart/quickstart.py

Copyright 2018 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

New format documentation:
https://developers.google.com/gmail/api/v1/reference

Old format documentation:
https://developers.google.com/resources/api-libraries/documentation/gmail/v1/python/latest/index.html
"""
import logging
import pickle
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from pprint import pformat
from subprocess import run
from typing import Dict, List, Optional, Tuple

import click
import rumps
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from dontforget.app import DontForgetApp
from dontforget.constants import DELAY, MISFIRE_GRACE_TIME
from dontforget.generic import UT, parse_interval
from dontforget.plugins.base import BasePlugin
from dontforget.settings import DEFAULT_DIRS, LOG_LEVEL

PYTHON_QUICKSTART_URL = "https://developers.google.com/gmail/api/quickstart/python"
GMAIL_BASE_URL = "https://mail.google.com/"
CHECK_NOW_LAST_CHECK = "Check now (last check: "

# If modifying these scopes, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)


class Menu(Enum):
    """Menu items."""

    CheckNow = f"{CHECK_NOW_LAST_CHECK}never)"
    NoNewMail = "No new mail"


# TODO: format_count() should be the str() or repr() of this dataclass
# @dataclass
# class MessageCount:
#     threads: int = 0
#     messages: int = 0
def format_count(threads: int, messages: int) -> str:
    """Format the count of threads and messages."""
    if threads == messages:
        return str(threads) if threads else ""
    return f"{threads} ({messages})"


class GMailPlugin(BasePlugin):
    """GMail plugin."""

    # TODO: self.important: Dict[str, MessageCount] = {}
    important: Dict[str, List[int]] = {}

    @property
    def name(self) -> str:
        """Plugin name."""
        return "GMail"

    def init_app(self, app: DontForgetApp) -> bool:
        """Add GMail jobs to the background scheduler.

        :return: True if all GMail accounts were authenticated with OAuth.
        """
        self.app = app
        current_host = socket.gethostname()

        all_authenticated = True
        # Read items in reversed order because they will be added to the menu always after the "GMail" menu
        for data in reversed(self.plugin_config):
            hosts = data.pop("hosts", None)
            if hosts and current_host not in hosts:
                logger.debug("%s: Ignoring email check on this host %s", data["email"], current_host)
                continue

            logger.debug("%s: Creating GMail job", data["email"])
            job = GMailJob(plugin=self, app=self.app, **data)
            if not job.authenticated:
                all_authenticated = False
            else:
                self.app.scheduler.add_job(job, "interval", misfire_grace_time=MISFIRE_GRACE_TIME, **job.trigger_args)

        return all_authenticated

    def reload_config(self) -> bool:
        """Update jobs with new intervals, trigger email check again."""  # TODO
        return True

    def update_important(self, email: str, threads: int = 0, messages: int = 0, clear: bool = False) -> None:
        """Update the count of important messages, grouped by email."""
        if clear:
            self.important[email] = [0, 0]
            return

        self.important[email][0] += threads
        self.important[email][1] += messages

        sum_threads = sum_messages = 0
        for count_threads, count_messages in self.important.values():
            sum_threads += count_threads
            sum_messages += count_messages
        important = format_count(sum_threads, sum_messages)
        if important:
            self.app.title = f"{UT.DoubleExclamationMark} {important}"
            return
        self.app.title = self.app.DEFAULT_TITLE


@dataclass
class Label:
    """A GMail label."""

    id: str
    name: str
    anchor: Optional[str] = None
    check_unread: bool = True
    special: bool = False
    min_threads: int = 0
    min_messages: int = 0


class LabelMenuItem(rumps.MenuItem):
    """A menu item for a GMail label."""

    label: Label


# TODO: inherit from UserList and keep internal dicts to search by id/name
#  from collections import UserList
class LabelCollection:
    """A collection of GMail labels."""

    SPECIAL_LABELS = (
        Label("INBOX", "Inbox", "inbox"),
        Label("UNREAD", "Unread"),
        Label("STARRED", "Starred", "starred"),
        Label("IMPORTANT", "Important", "imp"),
        Label("CHAT", "Chat", "chats"),
        Label("SENT", "Sent", "sent"),
        Label("DRAFT", "Drafts", "drafts"),
        Label("SPAM", "Spam", "spam"),
        Label("TRASH", "Trash", "trash"),
        Label("CATEGORY_PERSONAL", "Category/Personal"),
        Label("CATEGORY_SOCIAL", "Category/Social", "category/social"),
        Label("CATEGORY_UPDATES", "Category/Updates", "category/updates"),
        Label("CATEGORY_FORUMS", "Category/Forums", "category/forums"),
        Label("CATEGORY_PROMOTIONS", "Category/Promotions", "category/promotions"),
    )

    def __init__(self):
        """Init the collection with the special labels."""
        self._labels: Dict[str, Label] = {}
        for label in self.SPECIAL_LABELS:
            label.special = True
            # On special labels, only check the inbox by default
            label.check_unread = label.id == "INBOX"
            self.add(label)
        self.fetched = False

    def add(self, label: Label):
        """Add a label to the collection."""
        if label.id in self._labels:
            return

        if not label.special:
            label.anchor = "label/" + label.name.replace(" ", "+")
            label.check_unread = True

        self._labels[label.id] = label

    def items(self):
        """Return the labels as dictionary items."""
        return self._labels.items()


class GMailAPI:
    """GMail API wrapper."""

    def __init__(self, email: str) -> None:
        self.email = email.strip()
        config_dir = Path(DEFAULT_DIRS.user_config_dir)
        self.token_file = config_dir / f"{self.email}-token.pickle"
        self.credentials_file = config_dir / f"{self.email}-credentials.json"

        self.service = None
        self.labels = LabelCollection()

    def authenticate(self) -> bool:
        """Authenticate using the GMail API.

        The file token.pickle stores the user's access and refresh tokens, and is created automatically when the
        authorization flow completes for the first time.
        """
        if not self.credentials_file.exists():
            click.secho(f"Credential file not found for {self.email}.", fg="bright_red")
            click.echo("Click on the 'Enable the GMail API' button and save the JSON file as ", nl=False)
            click.secho(str(self.credentials_file), fg="green")

            # Open the URL on the browser
            run(["open", f"{PYTHON_QUICKSTART_URL}?email={self.email}"], check=False)

            # Open the folder on Finder
            run(["open", str(self.credentials_file.parent)], check=False)
            return False

        creds = None
        if self.token_file.exists():
            creds = pickle.load(self.token_file.open("rb"))

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0, _dummy=self.email)

            # Save the credentials for the next run
            pickle.dump(creds, self.token_file.open("wb"))

        self.service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return True

    def fetch_labels(self) -> bool:
        """Fetch GMail labels.

        :return: True if labels were fetched.
        """
        if not self.service or self.labels.fetched:
            return False

        request = self.service.users().labels().list(userId="me")
        response = request.execute()
        for label in response.get("labels") or []:
            self.labels.add(Label(label["id"], label["name"]))

        logger.debug("%s: %s", self.email, pformat(dict(self.labels.items()), width=200))
        self.labels.fetched = True
        return True

    def unread_count(self, label: Label) -> Tuple[int, int]:
        """Return the unread thread/message count for a label.

        See https://developers.google.com/gmail/api/v1/reference/users/labels/get.

        :return: A tuple with unread thread and unread message count.
        """
        if self.service and self.labels and label.check_unread:
            request = self.service.users().labels().get(id=label.id, userId="me")
            response = request.execute()
            return response["threadsUnread"], response["messagesUnread"]
        return -1, -1

        # TODO: how to read a single email message
        # for message_dict in response["messages"]:
        #     # https://developers.google.com/gmail/api/v1/reference/users/messages/get#python
        #     result_dict = messages.get(userId="me", id=message_dict["id"], format="full").execute()
        #     parts = result_dict["payload"]["parts"]
        #     for part in parts:
        #         body = base64.urlsafe_b64decode(part["body"]["data"].encode("ASCII"))
        #         print("-" * 50)
        #         pprint(body.decode(), width=200)


class GMailJob:
    """A job to check email on GMail."""

    # TODO: turn this into a source... the "source" concept should be revamped and cleaned.
    #  So many things have to be cleaned/redesigned in this project... it is currently a *huge* pile of mess.
    #  Flask/Docker/Telegram/PyObjC... they are either not needed anymore or they need refactoring to be used again.

    def __init__(
        self,
        *,
        plugin: GMailPlugin,
        app: DontForgetApp,
        email: str,
        check: str = None,
        labels: List[Dict[str, str]] = None,
    ):
        self.plugin = plugin
        self.app = app
        self.gmail = GMailAPI(email)
        self.authenticated = self.gmail.authenticate()
        self.trigger_args = parse_interval(check or "1 hour")
        self.menu: Optional[rumps.MenuItem] = None

        # TODO: update the existing labels in self.gmail.labels instead
        self.config_labels: List[Label] = []
        for data in labels or []:
            data.setdefault("id", data.get("name", ""))
            self.config_labels.append(Label(**data))  # type: ignore

        # Add a few seconds of delay before triggering the first request to GMail
        # TODO: Configure the optional delay on the config.toml file
        self.trigger_args.update(
            name=f"{self.__class__.__name__}: {email}", start_date=datetime.now() + timedelta(seconds=DELAY)
        )

    def add_to_menu(self, menuitem):
        """Add a sub-item to the menu of this email."""
        if self.menu is None:
            return
        self.menu.add(menuitem)

    def create_main_menu(self):
        """Create the main menu for this email."""
        if self.menu is not None:
            return

        # Add this email to the app menu
        logger.debug("%s: Creating GMail menu", self.gmail.email)
        self.menu = rumps.MenuItem(self.gmail.email)

        self.add_to_menu(rumps.MenuItem(Menu.CheckNow.value, callback=self.check_now_clicked))
        self.add_to_menu(rumps.separator)

        self.app.menu.insert_after(self.plugin.name, self.menu)

    def __call__(self, *args, **kwargs):
        """Check GMail for new mail on inbox and specific labels."""
        self.check_unread_labels()

    def check_now_clicked(self, sender: Optional[rumps.MenuItem]):
        """Callback executed when a check is manually requested."""
        self.check_unread_labels()

    def label_clicked(self, menu: LabelMenuItem):
        """Callback executed when a label menu item is clicked."""
        label: Label = menu.label
        url = f"{GMAIL_BASE_URL}#{label.anchor}?_email={self.gmail.email}"
        logger.debug("Opening URL on browser: %s", url)
        run(["open", url], check=False)

    def check_unread_labels(self):
        """Check unread labels."""
        self.create_main_menu()
        if self.menu is None:
            return

        self.app.title = UT.Hourglass

        self.gmail.fetch_labels()

        current_time = datetime.now().strftime("%H:%M:%S")
        logger.debug("Checking email %s at %s", self.gmail.email, current_time)
        last_checked_menu: rumps.MenuItem = self.menu[Menu.CheckNow.value]
        last_checked_menu.title = f"{CHECK_NOW_LAST_CHECK}{current_time})"

        new_mail = has_important = False
        total_unread_threads = total_unread_messages = 0
        self.plugin.update_important(self.gmail.email, clear=True)
        for _label_id, label in self.gmail.labels.items():
            config_label: Optional[Label] = None
            for i in self.config_labels:
                if label.name.casefold() == i.name.casefold():
                    config_label = i
                    break
            if config_label:
                if not config_label.check_unread:
                    continue
                # TODO: config labels and labels should be a single collection
                label.check_unread = config_label.check_unread
            elif not label.check_unread:
                continue

            menu_already_exists = label.name in self.menu
            unread_threads, unread_messages = self.gmail.unread_count(label)

            # Only show labels with unread messages
            if unread_threads <= 0 or unread_messages <= 0:
                if menu_already_exists:
                    # Remove the menu if it exists
                    del self.menu[label.name]
                continue

            if not menu_already_exists:
                label_menuitem = LabelMenuItem(label.name, callback=self.label_clicked)
                label_menuitem.label = label
                self.add_to_menu(label_menuitem)
            else:
                label_menuitem = self.menu[label.name]

            important = ""
            if config_label:
                if (config_label.min_threads and unread_threads >= config_label.min_threads) or (
                    config_label.min_messages and unread_messages >= config_label.min_messages
                ):
                    important = f"{UT.HeavyExclamationMarkSymbol}"
                    has_important = True
                    self.plugin.update_important(self.gmail.email, unread_threads, unread_messages)

            # Show unread count of threads for each label
            total_unread_threads += unread_threads
            total_unread_messages += unread_messages
            label_menuitem.title = f"{important}{label.name}: {format_count(unread_threads, unread_messages)}"
            new_mail = True

        important = f"{UT.HeavyExclamationMarkSymbol}" if has_important else ""
        envelope = ""
        if total_unread_threads > 0 or total_unread_messages > 0:
            envelope = f"{important}{UT.Envelope} {format_count(total_unread_threads, total_unread_messages)} | "
        self.menu.title = f"{envelope}{self.gmail.email}"

        if not new_mail:
            if Menu.NoNewMail.value not in self.menu:
                self.add_to_menu(Menu.NoNewMail.value)
        else:
            if Menu.NoNewMail.value in self.menu:
                del self.menu[Menu.NoNewMail.value]

        self.plugin.update_important(self.gmail.email)
