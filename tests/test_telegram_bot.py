"""Test Telegram bot."""
# pylint: disable=invalid-name,no-member,too-many-arguments
import time
from itertools import zip_longest
from queue import Queue
from unittest import mock

import arrow
import maya
import pytest

from dontforget.app import db
from dontforget.models import Alarm, Chore
from dontforget.telegram_bot import main_loop
from tests.factories import ChoreFactory


class TelegramAppMock:
    """A mock class to simulate interactions with the Telegram App."""

    CHAT_ID = 88466670
    FIRST_UPDATE_ID = 756866280
    FIRST_MESSAGE_ID = 2144

    def __init__(self, app):
        """Init instance."""
        self.app = app
        self.update_queue = Queue()
        self.mocked_send_message = mock.patch("telepot.Bot.sendMessage")
        self.update_id = self.FIRST_UPDATE_ID
        self.message_id = self.FIRST_MESSAGE_ID
        self.expected_replies = []

    def __enter__(self):
        """Mock methods and run the main loop."""
        self.mocked_send_message.start()

        main_loop(self.app, self.update_queue)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore mocked methods."""
        self.assert_messages()
        self.mocked_send_message.stop()

    def dict_message(self, text="", **kwargs):
        """Dict with message data."""
        default = {
            "message_id": self.next_message_id(),
            "chat": self.dict_user(type="private"),
            "date": 1482861515,
            "text": text,
        }
        default.update({"from": self.dict_user()})
        default.update(**kwargs)
        return default

    def dict_user(self, **kwargs):
        """Dict with user data."""
        return dict(id=self.CHAT_ID, first_name="Augusto", last_name="Andreoli", username="andreoliwa", **kwargs)

    def next_update_id(self):
        """Increment and return the next update ID.

        Simulating as if we had more than 1 update from the API server, in between messages.
        """
        self.update_id += 5
        return self.update_id

    def next_message_id(self):
        """Increment and return the next message ID.

        Simulating as if we had more than 1 update from the API server, in between messages.
        """
        self.message_id += 2
        return self.message_id

    def put_update(self, **kwargs):
        """Put an update in the queue."""
        self.update_queue.put(dict(update_id=self.next_update_id(), **kwargs))

    def type_command(self, command_plus_args: str, expected_reply: str):
        """Simulate the typing of a command in the Telegram App."""
        clean = "/{}".format(command_plus_args.lstrip("/"))
        command = clean.split()[0]
        self.put_update(
            message=self.dict_message(
                text=clean, entities=[{"type": "bot_command", "offset": 0, "length": len(command)}]
            )
        )
        self.expected_replies.append(expected_reply)

    def type_text(self, text: str, expected_reply: str):
        """Simulate the typing of text in the Telegram App."""
        self.put_update(message=self.dict_message(text=text))
        self.expected_replies.append(expected_reply)

    def assert_messages(self):
        """Assert that the bot answers with the expected replies."""
        # Wait for the messages to be processed in other threads.
        time.sleep(len(self.expected_replies) + 1.5)

        for mock_call, expected_reply in zip_longest(
            self.mocked_send_message.target.sendMessage.mock_calls, self.expected_replies
        ):
            call_args = mock_call[1]
            assert call_args[0] == self.CHAT_ID
            assert expected_reply in call_args[1]


def test_start_command(app):
    """Start command."""
    with TelegramAppMock(app) as telegram:
        telegram.type_command("start", "I'm a bot to help you with your chores.")
        telegram.type_text("xxx", "I don't understand what you mean.")
        telegram.type_command("start", "I'm a bot to help you with your chores.")


def test_overdue_command(app):
    """Overdue command."""
    with TelegramAppMock(app) as telegram:
        telegram.type_command("overdue", "You have no overdue chores, congratulations! \U0001F44F\U0001F3FB")


@pytest.mark.xfail(reason="Failing after conversion to PostgreSQL")
def test_spawn_alarm_on_overdue_command(app):
    """Spawn alarms on the overdue command."""
    assert app
    ChoreFactory(title="Something real")
    db.session.commit()

    with TelegramAppMock(app) as telegram:
        assert Alarm.query.count() == 0
        telegram.type_command("overdue", "Your overdue chores at:\n\n✅ /id_1: Something real")
    assert Alarm.query.count() == 1


@pytest.mark.xfail(reason="Failing after conversion to PostgreSQL")
def test_add_command(app):
    """Add some chores."""
    assert app
    assert Chore.query.count() == 0

    right_now = arrow.now()
    tomorrow_10 = maya.when("tomorrow 10:00")
    yesterday_9am = maya.when("yesterday 9am")
    yesterday_2pm = maya.when("yesterday 2pm")

    with TelegramAppMock(app) as telegram:
        telegram.type_command("add My first chore   , tomorrow 10:00", "The chore was added.")
        telegram.type_command("add Do it now", "The chore was added.")
        telegram.type_command("add Wash clothes , yesterday 9am , weekly ", "The chore was added.")
        telegram.type_command("add Shopping , yesterday 2pm , every 2 months ", "The chore was added.")

        # Add in 2 steps.
        help_message = (
            "To add a new chore, enter the following info (one per line or comma separated):\n"
            "\u2022 Title\n"
            "\u2022 (optional) First alarm. E.g.: today 10am, tomorrow 9pm, 20 Jan 2017...\n"
            "\u2022 (optional) Repetition. E.g.: once, weekly, every 3 days...\n"
            "Or choose /cancel to stop adding a new chore."
        )
        telegram.type_command("add", help_message)
        telegram.type_text("Christmas;25 Dec 2016,yearly", "The chore was added.")

        telegram.type_command("add", help_message)
        telegram.type_command("cancel", "Okay, no new chore then.")

    assert Chore.query.count() == 5
    assert Alarm.query.count() == 0
    first, do_it, wash, shopping, christmas = Chore.query.all()

    assert first.title == "My first chore"
    assert arrow.get(first.alarm_start).to("utc") == tomorrow_10.datetime()
    assert first.repetition is None

    assert do_it.title == "Do it now"
    # Both dates should have less than 10 seconds difference (the time of the test).
    assert (arrow.get(do_it.alarm_start).to("utc") - right_now).seconds < 10
    assert do_it.repetition is None

    assert wash.title == "Wash clothes"
    assert arrow.get(wash.alarm_start).to("utc") == yesterday_9am.datetime()
    assert wash.repetition == "weekly"

    assert shopping.title == "Shopping"
    assert arrow.get(shopping.alarm_start).to("utc") == yesterday_2pm.datetime()
    assert shopping.repetition == "every 2 months"

    assert christmas.title == "Christmas"
    assert arrow.get(christmas.alarm_start).to("utc") == maya.when("25 Dec 2016").datetime()
    assert christmas.repetition == "yearly"
