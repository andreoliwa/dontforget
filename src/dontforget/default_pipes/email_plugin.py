"""Email checker (Gmail/IMAP). It is not a source nor a target... yet.

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
from __future__ import annotations

import logging
import socket
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from pprint import pformat
from subprocess import run
from typing import Any

import click
import rumps
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build as build_google_api_client
from imbox import Imbox

from dontforget.app import BasePlugin, DontForgetApp
from dontforget.constants import DEFAULT_DELAY_SECONDS, MISFIRE_GRACE_TIME
from dontforget.generic import UT, parse_interval
from dontforget.settings import DEFAULT_DIRS, LOG_LEVEL

CHECK_NOW_LAST_CHECK = "Check now (last check: "

# If modifying these scopes, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)


class Menu(Enum):
    """Menu items."""

    CheckNow = f"{CHECK_NOW_LAST_CHECK}never)"
    OpenUnreadMessages = "Open unread messages"
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


class EmailPlugin(BasePlugin):
    """Email plugin (Gmail/IMAP)."""

    # TODO: self.important: Dict[str, MessageCount] = {}
    important: dict[str, list[int]] = {}

    @property
    def name(self) -> str:
        """Plugin name."""
        return "Email"

    def init_app(self, app: DontForgetApp) -> bool:
        """Add email jobs to the background scheduler.

        :return: True if all email accounts were authenticated (with OAuth in Gmail's case).
        """
        self.app = app
        current_host = socket.gethostname()

        all_authenticated = True
        # Read items in reversed order because they will be added to the menu always after the "Email" menu
        for data in reversed(self.plugin_config):
            hosts = data.pop("hosts", None)
            if hosts and current_host not in hosts:
                logger.debug("%s: Ignoring email check on this host %s", data["email"], current_host)
                continue

            # TODO: the YAML file schema should be validated with pydantic/attrs/something else
            open_apps = data.pop("open-apps", [])
            if open_apps:
                app_is_open = False
                for open_app in open_apps:
                    process = run(["pidof", open_app], capture_output=True, text=True)
                    if process.stdout:
                        app_is_open = True
                        break
                if not app_is_open:
                    logger.debug(
                        "%s: Ignoring email check because none of these apps are open %s", data["email"], open_apps
                    )
                    continue

            logger.debug("%s: Creating email job", data["email"])
            job = EmailJob(plugin=self, app=self.app, **data)
            if not job.authenticated:
                all_authenticated = False
            else:
                self.app.scheduler.add_job(
                    job,
                    "interval",
                    id=data["email"],
                    replace_existing=True,
                    misfire_grace_time=MISFIRE_GRACE_TIME,
                    **job.trigger_args,
                )

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
    """An email label."""

    id: str
    name: str
    anchor: str | None = None
    check_unread: bool = True
    special: bool = False
    min_threads: int = 0
    min_messages: int = 0


class LabelMenuItem(rumps.MenuItem):
    """A menu item for an email label."""

    label: Label


# TODO: inherit from UserList and keep internal dicts to search by id/name
#  from collections import UserList
class GmailLabelCollection:
    """A collection of Gmail labels."""

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
        self._labels: dict[str, Label] = {}
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


@dataclass(kw_only=True)
class Server:
    """Server information."""

    name: str
    host: str
    port: int
    webmail_url: str
    search_unread_anchor: str
    domains: list[str] = field(default_factory=list)
    api_class: type[ImapApi | GmailApi]


@dataclass
class BaseApi:
    """Base class for API wrappers."""

    server: Server
    email: str

    def build_url(self, anchor: str) -> str:
        """Build the web URL for a label."""
        return f"{self.server.webmail_url}{anchor}?_email={self.email}"

    def build_unread_url(self) -> str:
        """Build the web URL for the unread messages."""
        return f"{self.server.webmail_url}{self.server.search_unread_anchor}?_email={self.email}"


@dataclass
class GmailApi(BaseApi):
    """Gmail API wrapper."""

    gmail_client: Any | None = field(init=False)

    PYTHON_QUICKSTART_URL = "https://developers.google.com/gmail/api/quickstart/python"
    CONSOLE_CREDENTIALS_URL = "https://console.cloud.google.com/apis/credentials"

    def __post_init__(self) -> None:
        self.labels = GmailLabelCollection()

    def authenticate(self, password: str | None = None) -> bool:
        """Authenticate using the Gmail API.

        The file token.pickle stores the user's access and refresh tokens, and is created automatically when the
        authorization flow completes for the first time.
        """
        config_dir = Path(DEFAULT_DIRS.user_config_dir)
        token_file = config_dir / f"{self.email}-token.json"
        credentials_file = config_dir / f"{self.email}-credentials.json"
        if not credentials_file.exists():
            click.secho(f"Credential file not found for {self.email}.", fg="bright_red")
            click.echo("Follow the steps and save the OAuth 2.0 Client-ID JSON file as ", nl=False)
            click.secho(str(credentials_file), fg="green")

            # Open the URL on the browser
            run(["open", f"{self.PYTHON_QUICKSTART_URL}?for_finickyjs={self.email}"], check=False)
            run(["open", f"{self.CONSOLE_CREDENTIALS_URL}?for_finickyjs={self.email}"], check=False)

            # Open the folder on Finder
            run(["open", str(credentials_file.parent)], check=False)
            return False

        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if token_file.exists():
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
                creds = flow.run_local_server(port=0, for_finickyjs=self.email)
            # Save the credentials for the next run
            token_file.write_text(creds.to_json())

        self.gmail_client = build_google_api_client("gmail", "v1", credentials=creds)
        return True

    def fetch_labels(self) -> bool:
        """Fetch Gmail labels.

        :return: True if labels were fetched.
        """
        if not self.gmail_client or self.labels.fetched:
            return False

        request = self.gmail_client.users().labels().list(userId="me")
        response = request.execute()
        for label in response.get("labels") or []:
            self.labels.add(Label(label["id"], label["name"]))

        logger.debug("%s: %s", self.email, pformat(dict(self.labels.items()), width=200))
        self.labels.fetched = True
        return True

    def unread_count(self, label: Label) -> tuple[int, int]:
        """Return the unread thread/message count for a label.

        See https://developers.google.com/gmail/api/v1/reference/users/labels/get.

        :return: A tuple with unread thread and unread message count.
        """
        if self.gmail_client and self.labels and label.check_unread:
            request = self.gmail_client.users().labels().get(id=label.id, userId="me")
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


@dataclass
class ImapApi(BaseApi):
    """IMAP API wrapper."""

    imbox: Imbox = field(init=False)
    labels: dict[str, Label] = field(init=False, default_factory=dict)

    def authenticate(self, password: str | None = None) -> bool:
        """Authenticate using IMAP."""
        self.imbox = Imbox(
            self.server.host,
            port=self.server.port,
            username=self.email.strip(),
            password=password,
            ssl=True,
            ssl_context=None,
            starttls=False,
        )
        return True

    def fetch_labels(self) -> bool:
        """Fetch IMAP labels."""
        self.labels["INBOX"] = Label("INBOX", "Inbox", "inbox")
        return True

    def unread_count(self, label: Label) -> tuple[int, int]:
        """Return the unread thread/message count for a label."""
        count = len(self.imbox.messages(folder=label.id, unread=True))
        return count, count


ALLOWED_SERVERS = [
    Server(
        name="Fastmail",
        host="imap.fastmail.com",
        port=993,
        webmail_url="https://app.fastmail.com/mail/",
        search_unread_anchor="search:is%3Aunread/",
        domains=[
            "fastmail.com",
            "sent.com",
            "fea.st",
            "fastmail.de",
        ],
        api_class=ImapApi,
    ),
    Server(
        name="Gmail",
        host="",
        port=0,
        webmail_url="https://mail.google.com/#",
        search_unread_anchor="search/is%3Aunread",
        domains=[
            "gmail.com",
            "googlemail.com",
        ],
        api_class=GmailApi,
    ),
]


def find_server_by_domain(email: str) -> Server:
    """Find the IMAP server by the domain of the email address."""
    for server in ALLOWED_SERVERS:
        for domain in server.domains:
            if email.endswith(domain):
                return server
    raise ValueError(f"IMAP server not configured for this domain: {email}")


class EmailJob:
    """A job to check email."""

    # TODO: turn this into a source... the "source" concept should be revamped and cleaned.

    def __init__(
        self,
        *,
        plugin: EmailPlugin,
        app: DontForgetApp,
        email: str,
        check: str = None,
        labels: list[dict[str, str]] = None,
        password: str = None,
        delay: int = DEFAULT_DELAY_SECONDS,
    ):
        self.plugin = plugin
        self.app = app
        server: Server = find_server_by_domain(email)
        self.email_api: ImapApi | GmailApi = server.api_class(server, email)
        self.authenticated = self.email_api.authenticate(password)
        self.trigger_args = parse_interval(check or "1 hour")
        self.menu: rumps.MenuItem | None = None

        # TODO: update the existing labels in self.email_api.labels instead
        self.config_labels: list[Label] = []
        for data in labels or []:
            data.setdefault("id", data.get("name", ""))
            self.config_labels.append(Label(**data))  # type: ignore

        # Add a few seconds of delay before triggering the first request to Gmail
        # TODO: Configure the optional delay on the config.toml file
        self.trigger_args.update(
            name=f"{self.__class__.__name__}: {email}", start_date=datetime.now() + timedelta(seconds=delay)
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
        logger.debug("%s: Creating email menu", self.email_api.email)
        self.menu = rumps.MenuItem(self.email_api.email)

        self.add_to_menu(rumps.MenuItem(Menu.CheckNow.value, callback=self.check_now_clicked))
        self.add_to_menu(rumps.MenuItem(Menu.OpenUnreadMessages.value, callback=self.open_unread_messages_clicked))
        self.add_to_menu(rumps.separator)

        self.app.menu.insert_after(self.plugin.name, self.menu)

    def __call__(self, *args, **kwargs):
        """Check Gmail for new mail on inbox and specific labels."""
        self.check_unread_labels()

    def check_now_clicked(self, sender: rumps.MenuItem | None):
        """Callback executed when a check is manually requested."""
        self.check_unread_labels()

    def open_unread_messages_clicked(self, sender: rumps.MenuItem | None):
        """Callback executed when the user wants to open the unread messages on the browser."""
        url = self.email_api.build_unread_url()
        logger.debug("Opening URL on browser: %s", url)
        run(["open", url], check=False)

    def label_clicked(self, menu: LabelMenuItem):
        """Callback executed when a label menu item is clicked."""
        label: Label = menu.label
        url = self.email_api.build_url(label.anchor)
        logger.debug("Opening URL on browser: %s", url)
        run(["open", url], check=False)

    def check_unread_labels(self):
        """Check unread labels."""
        self.create_main_menu()
        if self.menu is None:
            return

        self.app.title = UT.Hourglass

        self.email_api.fetch_labels()

        current_time = datetime.now().strftime("%H:%M:%S")
        logger.debug("Checking email %s at %s", self.email_api.email, current_time)
        last_checked_menu: rumps.MenuItem = self.menu[Menu.CheckNow.value]
        last_checked_menu.title = f"{CHECK_NOW_LAST_CHECK}{current_time})"

        new_mail = has_important = False
        total_unread_threads = total_unread_messages = 0
        self.plugin.update_important(self.email_api.email, clear=True)
        for _label_id, label in self.email_api.labels.items():
            config_label: Label | None = None
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
            unread_threads, unread_messages = self.email_api.unread_count(label)

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
                    self.plugin.update_important(self.email_api.email, unread_threads, unread_messages)

            # Show unread count of threads for each label
            total_unread_threads += unread_threads
            total_unread_messages += unread_messages
            label_menuitem.title = f"{important}{label.name}: {format_count(unread_threads, unread_messages)}"
            new_mail = True

        important = f"{UT.HeavyExclamationMarkSymbol}" if has_important else ""
        envelope = ""
        if total_unread_threads > 0 or total_unread_messages > 0:
            envelope = f"{important}{UT.Envelope} {format_count(total_unread_threads, total_unread_messages)} | "
        self.menu.title = f"{envelope}{self.email_api.email}"

        if not new_mail:
            if Menu.NoNewMail.value not in self.menu:
                self.add_to_menu(Menu.NoNewMail.value)
        else:
            if Menu.NoNewMail.value in self.menu:
                del self.menu[Menu.NoNewMail.value]

        self.plugin.update_important(self.email_api.email)
