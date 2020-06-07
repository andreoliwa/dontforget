"""Gmail checker. It is not a source nor a target... yet."""
from datetime import datetime, timedelta
from typing import Any, Dict

from rumps import notification

from dontforget.constants import DELAY


class GmailJob:
    """A job to check email on Gmail."""

    # TODO: turn this into a source... the "source" concept should be revamped and cleaned.
    #  So many things have to be cleaned/redesigned in this project... it is currently a *huge* pile of mess.
    #  Flask/Docker/Telegram/PyObjC... they are either not needed anymore or they need refactoring to be used again.

    def __init__(self, *, email=None, password=None, interval: Dict[str, Any] = None):
        self.email = email
        self.password = password
        self.trigger_args = interval or {}

        # Add a few seconds of delay before triggering the first request to Gmail
        # Configure the optional delay on the config.toml file
        self.trigger_args.update(
            name=f"{self.__class__.__name__}: {email}", start_date=datetime.now() + timedelta(seconds=DELAY)
        )

    def __call__(self, *args, **kwargs):
        """Send Dramatiq task to check Gmail."""
        # FIXME: this is only a test. Replace this by the actual Dramatiq task to check email
        values = "Gmail", f"Email: {self.email}", "The time is: %s" % datetime.now()
        notification(*values)
        print(*values)
