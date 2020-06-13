"""Gmail checker. It is not a source nor a target... yet."""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from rumps import notification

from dontforget.constants import DELAY


def parse_interval_from(text: Optional[str]) -> Dict[str, Any]:
    """Parse an interval from text.

    >>> parse_interval_from("10 minutes")
    {'minutes': 10}
    >>> parse_interval_from(" hours  5  ")
    {'hours': 5}
    >>> parse_interval_from(None)
    {}
    >>> parse_interval_from("  ")
    {}
    >>> parse_interval_from(" 15 , shenanigans ,,  ")
    {'shenanigans': 15}
    >>> parse_interval_from(" ??? 12 ")
    {}
    >>> parse_interval_from(" ??? ")
    {}
    >>> parse_interval_from(" xxx ")
    {}
    >>> parse_interval_from(" 3 ")
    {}

    :param text: The text to be parsed.
    :return: Parsed dict.
    """
    clean_text = (text or "").strip()
    if not clean_text:
        return {}
    number = 0
    key = ""
    for part in clean_text.split(" "):
        if not part:
            continue
        if part.isnumeric():
            number = int(part)
        elif part.isalpha():
            key = part.strip()
    return {key: number} if key and number else {}


class GmailJob:
    """A job to check email on Gmail."""

    # TODO: turn this into a source... the "source" concept should be revamped and cleaned.
    #  So many things have to be cleaned/redesigned in this project... it is currently a *huge* pile of mess.
    #  Flask/Docker/Telegram/PyObjC... they are either not needed anymore or they need refactoring to be used again.

    def __init__(self, *, email: str = None, check: str = None, labels: Dict[str, str] = None):
        self.email = email
        self.trigger_args = parse_interval_from(check)

        # Add a few seconds of delay before triggering the first request to Gmail
        # Configure the optional delay on the config.toml file
        self.trigger_args.update(
            name=f"{self.__class__.__name__}: {email}", start_date=datetime.now() + timedelta(seconds=DELAY)
        )

    def __call__(self, *args, **kwargs):
        """Check Gmail for new mail on inbox and specific labels."""
        # FIXME: replace this by the actual email check
        values = "Gmail", f"Email: {self.email}", "The time is: %s" % datetime.now()
        notification(*values)
        print(*values)
