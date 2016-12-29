"""Test Telegram bot."""
# pylint: disable=invalid-name,no-member,too-many-arguments
import time
from queue import Queue
from unittest import mock
from unittest.mock import call

from flask import current_app

from dontforget.ui.telegram_bot import main_loop


class TelegramAppMock:
    """A mock class to simulate interactions with the Telegram App."""

    CHAT_ID = 88466670
    FIRST_UPDATE_ID = 756866280
    FIRST_MESSAGE_ID = 2144

    def __init__(self):
        """Init instance."""
        self.update_queue = Queue()
        self.mocked_send_message = mock.patch('telepot.Bot.sendMessage')
        self.update_id = self.FIRST_UPDATE_ID
        self.message_id = self.FIRST_MESSAGE_ID
        self.expected_replies = []

    def __enter__(self):
        """Mock methods and run the main loop."""
        self.mocked_send_message.start()

        main_loop(current_app, self.update_queue)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore mocked methods."""
        self.assert_messages()
        self.mocked_send_message.stop()

    def dict_message(self, text='', **kwargs):
        """Dict with message data."""
        default = dict(
            message_id=self.next_message_id(),
            chat=self.dict_user(type='private'),
            date=1482861515,
            text=text,
        )
        default.update({'from': self.dict_user()})
        default.update(**kwargs)
        return default

    def dict_user(self, **kwargs):
        """Dict with user data."""
        return dict(id=self.CHAT_ID, first_name='Augusto', last_name='Andreoli', username='andreoliwa', **kwargs)

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

    def type_command(self, command: str, expected_reply: str):
        """Simulate the typing of a command in the Telegram App."""
        clean_command = '/{}'.format(command.lstrip('/'))
        self.put_update(message=self.dict_message(
            text=clean_command,
            entities=[dict(type='bot_command', offset=0, length=len(clean_command))]
        ))
        self.expected_replies.append(expected_reply)

    def type_text(self, text: str, expected_reply: str):
        """Simulate the typing of text in the Telegram App."""
        self.put_update(message=self.dict_message(text=text))
        self.expected_replies.append(expected_reply)

    def assert_messages(self):
        """Assert that the bot answers with the expected replies."""
        expected_calls = [call(self.CHAT_ID, message) for message in self.expected_replies]

        # Wait for the messages to be processed in another thread.
        time.sleep(len(expected_calls) + 1)

        assert self.mocked_send_message.target.sendMessage.mock_calls == expected_calls


def test_start_command():
    """Start command."""
    with TelegramAppMock() as telegram:
        telegram.type_command('start', "I'm a bot to help you with your chores.")
        telegram.type_text('xxx', "I don't understand what you mean.")
        telegram.type_command('start', "I'm a bot to help you with your chores.")

# def test_overdue_command():
#     """Overdue command."""
#     with TelegramAppMock() as telegram:
