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

"""
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

import click
from appdirs import AppDirs
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from rumps import notification

from dontforget.constants import APP_NAME, DELAY
from dontforget.generic import parse_interval

PYTHON_QUICKSTART_URL = "https://developers.google.com/gmail/api/quickstart/python"

# If modifying these scopes, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GMailAPI:
    """GMail API wrapper."""

    def __init__(self, email: str) -> None:
        self.email = email.strip()
        config_dir = Path(AppDirs(APP_NAME).user_config_dir)
        self.token_file = config_dir / f"{self.email}-token.pickle"
        self.credentials_file = config_dir / f"{self.email}-credentials.json"

        self.service = None
        self.labels: Dict[str, str] = {}

    def authenticate(self) -> bool:
        """Authenticate using the GMail API.

        The file token.pickle stores the user's access and refresh tokens, and is created automatically when the
        authorization flow completes for the first time.
        """
        from subprocess import run

        if not self.credentials_file.exists():
            click.secho(f"Credential file not found for {self.email}.", fg="bright_red")
            click.echo("Click on the 'Enable the GMail API' button and save the JSON file as ", nl=False)
            click.secho(str(self.credentials_file), fg="green")

            # Open the URL on the browser
            run(["open", f"{PYTHON_QUICKSTART_URL}?email={self.email}"])

            # Open the folder on Finder
            run(["open", str(self.credentials_file.parent)])
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

        self.service = build("gmail", "v1", credentials=creds)
        # FIXME:
        # # https://developers.google.com/resources/api-libraries/documentation/gmail/v1/python/latest/gmail_v1.users.messages.html#get
        # import base64
        # messages = service.users().messages()
        # request = messages.list(userId="me", labelIds="Label_7807279795529054300")
        # results = request.execute()
        # for message_dict in results["messages"]:
        #     # https://developers.google.com/gmail/api/v1/reference/users/messages/get#python
        #     result_dict = messages.get(userId="me", id=message_dict["id"], format="full").execute()
        #     parts = result_dict["payload"]["parts"]
        #     for part in parts:
        #         body = base64.urlsafe_b64decode(part["body"]["data"].encode("ASCII"))
        #         print("-" * 50)
        #         pprint(body.decode(), width=200)
        return True

    def fetch_labels(self) -> bool:
        """Fetch GMail labels."""
        if not self.service:
            return False
        self.labels = {}
        results = self.service.users().labels().list(userId="me").execute()
        for label in results.get("labels") or []:
            self.labels[label["name"]] = label["id"]
        return True


class GMailJob:
    """A job to check email on GMail."""

    # TODO: turn this into a source... the "source" concept should be revamped and cleaned.
    #  So many things have to be cleaned/redesigned in this project... it is currently a *huge* pile of mess.
    #  Flask/Docker/Telegram/PyObjC... they are either not needed anymore or they need refactoring to be used again.

    def __init__(self, *, email: str, check: str, labels: Dict[str, str] = None):
        self.gmail = GMailAPI(email)
        self.authenticated = self.gmail.authenticate()
        self.gmail.fetch_labels()
        self.trigger_args = parse_interval(check)

        # Add a few seconds of delay before triggering the first request to GMail
        # Configure the optional delay on the config.toml file
        self.trigger_args.update(
            name=f"{self.__class__.__name__}: {email}", start_date=datetime.now() + timedelta(seconds=DELAY)
        )

    def __call__(self, *args, **kwargs):
        """Check GMail for new mail on inbox and specific labels."""
        # FIXME: replace this by the actual email check
        values = "GMail", self.gmail.email, "The time is: %s" % datetime.now()
        notification(*values)
        print(*values)
