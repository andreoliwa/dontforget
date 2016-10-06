"""Telegram bot module."""
import logging
from datetime import datetime
from enum import Enum
from functools import wraps

from telegram import ReplyKeyboardMarkup
from telegram.ext import CommandHandler, ConversationHandler, Filters, MessageHandler, RegexHandler, Updater

from dontforget.models import Alarm, AlarmState
from dontforget.settings import UI_TELEGRAM_BOT_TOKEN


def bot_callback(method):
    """Decorator for command methods in the :py:class:`TelegramBot` class."""
    @wraps(method)
    def method_wrapper(self):
        """Wrapper around methods in the :py:class:`TelegramBot` class.

        :param self: A :py:class:`TelegramBot` instance.
        :return: Pointer to the function called by the framework.
        """
        def function_called_by_bot_framework(bot, update, **kwargs):   # pylint: disable=invalid-name
            """Function called by the Telegram bot framework.

            :param bot: Telegram bot object sent by the framework.
            :param update: Message update
            :param kwargs: Extra arguments when `pass_args=True` or other options are used.
            :return: Result of calling `method(self)`.
            """
            self.bot = bot
            self.update = update
            self.text = update.message.text
            self.args = kwargs.pop('args', None)

            # We need an app context to query the database.
            with self.app.app_context():
                return method(self)
        return function_called_by_bot_framework
    return method_wrapper


class TelegramBot:
    """Telegram bot to answer commands."""

    class State(Enum):
        """States for the conversation."""
        DETAILS = 1
        ACTION = 2
        OVERDUE = 3

    def __init__(self, app):
        """Init the instance of the bot.

        Some properties will be filled by the decorator :py:meth:`bot_callback()`.

        :param app: Flask app.
        """
        self.app = app
        self.bot = None
        self.update = None
        self.args = None
        self.text = None
        self.last_alarm_id = None

    def send_message(self, text, reply_markup=None):
        """Send a message to the Telegram chat.

        :param text: Text to send.
        :param reply_markup: Optional buttons/markup to the chat.
        """
        self.bot.send_message(chat_id=self.update.message.chat_id, text=text, reply_markup=reply_markup)

    @bot_callback
    def start(self):
        """Start the bot with a friendly message."""
        self.send_message("I'm a bot to help you with your chores.")

    @bot_callback
    def overdue(self):
        """Overdue chores, most recent first."""
        right_now = datetime.now()
        # pylint: disable=no-member
        query = Alarm.query.filter(Alarm.current_state == AlarmState.UNSEEN,
                                   Alarm.next_at <= right_now).order_by(Alarm.next_at.desc())
        strings = []
        reply_keyboard = []
        pair = []
        for index, alarm in enumerate(query.all()):
            short = '{}: {}'.format(alarm.id, alarm.chore.title[:30])
            long = '\u2705 {}: {}'.format(alarm.id, alarm.one_line)  # :alarm_clock:
            pair.append(short)
            if (index + 1) % 2 == 0:
                reply_keyboard.append(pair)
                pair = []
            strings.append(long)

        # Remaining buttons.
        if pair:
            reply_keyboard.append(pair)

        self.update.message.reply_text(
            'Those are your overdue chores:\n\n{chores}'.format(chores='\n'.join(strings)),
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

        return self.State.DETAILS

    @bot_callback
    def show_alarm_details(self):
        """Show options for a chore."""
        self.last_alarm_id = int(self.text.split(':')[0])
        alarm = Alarm.query.get(self.last_alarm_id)  # pylint: disable=no-member
        keyboard = [['Skip', 'Snooze'], ['Complete', 'Abort']]
        self.update.message.reply_text(
            'What do you want to do with this alarm?\n{}'.format(alarm.one_line),
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return self.State.ACTION

    @bot_callback
    def choose_action(self):
        """Choose an action for the alarm."""
        self.update.message.reply_text('Chosen action was to {} the alarm {}'.format(self.text, self.last_alarm_id))
        return self.State.OVERDUE

    @bot_callback
    def cancel(self):
        """Cancel the conversation."""
        user = self.update.message.from_user
        self.update.message.reply_text('Bye! I hope we can talk again some day, {}.'.format(user.first_name))
        return ConversationHandler.END

    def run_loop(self):
        """Run the main loop for the Telegram bot."""
        if not UI_TELEGRAM_BOT_TOKEN:
            print('Telegram bot token is not defined')
            return

        updater = Updater(token=UI_TELEGRAM_BOT_TOKEN)
        dispatcher = updater.dispatcher
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

        handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', self.start()),
                CommandHandler('overdue', self.overdue())
            ],
            states={
                self.State.DETAILS: [MessageHandler([Filters.text], self.show_alarm_details())],
                self.State.ACTION: [RegexHandler('^(Skip|Snooze|Complete|Abort)$', self.choose_action())],
            },
            fallbacks=[CommandHandler('cancel', self.cancel())],
            allow_reentry=True
        )
        dispatcher.add_handler(handler)

        updater.start_polling()
        updater.idle()
