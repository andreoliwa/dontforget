"""Email sources (Fastmail, Gmail, etc.)."""
from typing import Iterator, Optional
from urllib.parse import quote_plus

import pendulum
from imbox import Imbox

from dontforget.pipes import BaseSource
from dontforget.typedefs import JsonDict


class EmailSource(BaseSource):
    """Email source."""

    imbox: Imbox
    current_uid: Optional[bytes] = None
    search_url: str
    search_date_format: str
    mark_read = False
    archive = False
    archive_folder: str

    def pull(self, connection_info: JsonDict) -> Iterator[JsonDict]:
        """Pull emails from Gmail."""
        self.imbox = Imbox(
            connection_info["hostname"],
            port=connection_info.get("port", None),
            username=connection_info["user"],
            password=connection_info["password"],
            ssl=True,
            ssl_context=None,
            starttls=False,
        )
        self.search_url = connection_info["search_url"]
        self.search_date_format = connection_info["search_date_format"]
        self.mark_read = connection_info.get("mark_read", False)
        self.archive = connection_info.get("archive", False)
        self.archive_folder = connection_info["archive_folder"]

        kwargs = {}
        from_ = connection_info.get("from")
        if from_:
            kwargs["sent_from"] = from_
        label = connection_info.get("label")
        if label:
            kwargs.update(folder="all", label=label)
        folder = connection_info.get("folder")
        if folder:
            kwargs.update(folder=folder)
        messages = self.imbox.messages(**kwargs)
        if not messages:
            return []

        for uid, message in messages:
            self.current_uid = uid
            date = pendulum.instance(message.parsed_date).date()
            url = self.build_search_url(from_, date, date.add(days=1))
            subject: str = message.subject
            yield {
                "uid": uid.decode(),
                "url": url,
                "subject": " ".join(subject.splitlines()),
                "parsed_date": message.parsed_date.isoformat(),
            }

    def build_search_url(self, from_: str = None, after: pendulum.Date = None, before: pendulum.Date = None) -> str:
        """Build the Gmail search URL."""
        search_terms = []
        if from_:
            search_terms.append(f"from:({from_})")
        if after:
            search_terms.append(f"after:{after.format(self.search_date_format)}")
        if before:
            search_terms.append(f"before:{before.format(self.search_date_format)}")

        quoted_terms = quote_plus(" ".join(search_terms))
        return f"{self.search_url}{quoted_terms}"

    def on_success(self):
        """Mark email as read and/or archive it, if requested."""
        if not self.current_uid:
            return
        if self.mark_read:
            self.imbox.mark_seen(self.current_uid)
        if self.archive:
            self.imbox.move(self.current_uid, self.archive_folder)