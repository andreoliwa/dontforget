"""Telegram bot module."""
import logging
from datetime import datetime
from functools import wraps

import telegram
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

from dontforget.models import Alarm, AlarmState
from dontforget.settings import UI_TELEGRAM_BOT_TOKEN


def handler_callback(method):
    """Decorator for command methods in the :py:class:`TelegramBot` class."""
    @wraps(method)
    def method_wrapper(self):
        """Wrapper around methods in the :py:class:`TelegramBot` class.

        :param self: A :py:class:`TelegramBot` instance.
        :return: Pointer to the function called by the framework.
        """
        def function_called_by_bot_framework(bot, update, args=None):   # pylint: disable=invalid-name
            """Function called by the Telegram bot framework.

            Don't change the names of the arguments; the framework expects them.

            :param bot: Telegram bot object sent by the framework.
            :param update: Message update
            :param args: Extra arguments when `pass_args=True` is used.
            :return: Result of calling `method(self)`.
            """
            self.bot = bot
            self.update = update
            self.args = args
            return method(self)
        return function_called_by_bot_framework
    return method_wrapper


class TelegramBot:
    """Telegram bot to answer commands."""

    def __init__(self, app):
        """Init the instance of the bot.

        Some properties will be filled by the decorator :py:meth:`handler_callback()`.

        :param app: Flask app.
        """
        self.app = app
        self.bot = None
        self.update = None
        self.args = None

    def send_message(self, text, reply_markup=None):
        """Send a message to the Telegram chat.

        :param text: Text to send.
        :param reply_markup: Optional buttons/markup to the chat.
        """
        self.bot.send_message(chat_id=self.update.message.chat_id, text=text, reply_markup=reply_markup)

    @handler_callback
    def start(self):
        """Start the bot with a friendly message."""
        self.send_message("I'm a bot to help you with your chores.")

    @handler_callback
    def echo(self):
        """Echo a message."""
        self.send_message('Current time: {0}, text received: {1}'.format(
            datetime.now().isoformat(), self.update.message.text))

    @handler_callback
    def caps(self):
        """Change text to uppercase."""
        self.send_message(' '.join(self.args).upper())

    @handler_callback
    def chore(self):
        """Show options for a chore."""
        custom_keyboard = [['Skip', 'Snooze'], ['Complete', 'Abort']]
        self.send_message('What do you want to do with this chore?', telegram.ReplyKeyboardMarkup(custom_keyboard))

    @handler_callback
    def overdue(self):
        """Overdue chores, most recent first."""
        right_now = datetime.now()
        with self.app.app_context():
            # pylint: disable=no-member
            query = Alarm.query.filter(Alarm.current_state == AlarmState.UNSEEN,
                                       Alarm.next_at <= right_now).order_by(Alarm.next_at.desc())
            strings = []
            buttons = []
            pair = []
            for index, unseen_alarm in enumerate(query.all()):
                pair.append('Chore {}'.format(index + 1))
                if (index + 1) % 3 == 0:
                    buttons.append(pair)
                    pair = []
                strings.append('{}: {}'.format(index + 1, unseen_alarm.one_line))

            # Remaining buttons.
            if pair:
                buttons.append(pair)

            self.send_message('Those are your overdue chores:\n{}'.format('\n'.join(strings)),
                              telegram.ReplyKeyboardMarkup(buttons))

    @handler_callback
    def unknown(self):
        """Unknown command."""
        self.send_message("Sorry, I didn't understand that command.")

    def run_loop(self):
        """Run the main loop for the Telegram bot."""
        if not UI_TELEGRAM_BOT_TOKEN:
            print('Telegram bot token is not defined')
            return

        updater = Updater(token=UI_TELEGRAM_BOT_TOKEN)
        dispatcher = updater.dispatcher
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

        # TODO: Remove dummy commands
        handlers = (
            CommandHandler('start', self.start()),
            MessageHandler([Filters.text], self.echo()),
            CommandHandler('caps', self.caps(), pass_args=True),
            CommandHandler('chore', self.chore()),
            CommandHandler('overdue', self.overdue()),
            # This one should always be the last one:
            MessageHandler([Filters.command], self.unknown()),
        )
        for handler in handlers:
            dispatcher.add_handler(handler)

        updater.start_polling()
        updater.idle()
