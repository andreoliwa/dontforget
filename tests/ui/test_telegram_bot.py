"""Test Telegram bot."""
# pylint: disable=invalid-name,no-member,too-many-arguments
import time
from queue import Queue
from unittest import mock

from flask import current_app

from dontforget.ui.telegram_bot import main_loop


class TelegramAppMock:
    """A mock class to simulate interactions with the Telegram App."""

    CHAT_ID = 88466670

    def __init__(self):
        """Init instance."""
        self.update_queue = Queue()
        self.mocked_send_message = mock.patch('telepot.Bot.sendMessage')

    def __enter__(self):
        """Mock methods and run the main loop."""
        self.mocked_send_message.start()

        main_loop(current_app, self.update_queue)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore mocked methods."""
        self.mocked_send_message.stop()

    def type_command(self, command: str):
        """Simulate the typing of a command in the Telegram App."""
        clean_command = '/{}'.format(command.lstrip('/'))
        self.update_queue.put(dict(update_id=756866280, message={
            'message_id': 2144,
            'from': dict(id=self.CHAT_ID, first_name='Augusto', last_name='Andreoli', username='andreoliwa'),
            'chat': dict(id=self.CHAT_ID, first_name='Augusto', last_name='Andreoli', username='andreoliwa',
                         type='private'),
            'date': 1482861515,
            'text': clean_command,
            'entities': [dict(type='bot_command', offset=0, length=len(clean_command))]
        }))

    def assert_message(self, expected_text):
        """Assert that the bot answers with the expected text."""
        time.sleep(.1)  # Wait for the message to be processed in another thread.
        self.mocked_send_message.target.sendMessage.assert_called_with(self.CHAT_ID, expected_text)


def test_start_command():
    """Start command."""
    with TelegramAppMock() as telegram:
        telegram.type_command('start')
        telegram.assert_message("I'm a bot to help you with your chores.")
