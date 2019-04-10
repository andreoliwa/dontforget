"""Gmail."""
from typing import Iterator
from urllib.parse import quote_plus

import pendulum
from imbox import Imbox

from dontforget.pipes import BaseSource
from dontforget.typedefs import JsonDict


class GmailSource(BaseSource):
    """Gmail source."""

    SEARCH_URL = "https://mail.google.com/mail/u/0/#search/"
    DATE_FORMAT = "Y/M/D"

    def pull(self, connection_info: JsonDict) -> Iterator[JsonDict]:
        """Pull emails from Gmail."""
        imbox = Imbox(
            "imap.gmail.com",
            username=connection_info["user"],
            password=connection_info["password"],
            ssl=True,
            ssl_context=None,
            starttls=False,
        )

        kwargs = {}
        from_ = connection_info.get("from")
        if from_:
            kwargs["sent_from"] = from_
        label = connection_info.get("label")
        if label:
            kwargs.update(folder="all", label=label)
        messages = imbox.messages(**kwargs)
        if not messages:
            return []

        for uid, message in messages:
            date = pendulum.instance(message.parsed_date).date()
            after = date.subtract(days=1)
            before = date.add(days=1)
            url = self.build_search_url(from_, after, before)
            yield {
                "uid": uid.decode(),
                "url": url,
                "subject": message.subject,
                "parsed_date": message.parsed_date.isoformat(),
            }

    def build_search_url(self, from_: str = None, after: pendulum.Date = None, before: pendulum.Date = None) -> str:
        """Build the Gmail search URL."""
        search_terms = []
        if from_:
            search_terms.append(f"from:({from_})")
        if after:
            search_terms.append(f"after:{after.format(self.DATE_FORMAT)}")
        if before:
            search_terms.append(f"before:{before.format(self.DATE_FORMAT)}")

        quoted_terms = quote_plus(" ".join(search_terms))
        return f"{self.SEARCH_URL}{quoted_terms}"
