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


class TelegramBot:  # pylint: disable=too-many-instance-attributes
    """Telegram bot to answer commands."""

    class Actions(Enum):
        """Actions that can be performed on an alarm."""
        COMPLETE = 'Complete'
        SNOOZE = 'Snooze'
        SKIP = 'Skip'
        TRACK = 'Track'
        STOP = 'Stop series'

    ACTION_BUTTONS = [Actions.COMPLETE.value, Actions.SNOOZE.value, Actions.SKIP.value,
                      Actions.TRACK.value, Actions.STOP.value]
    SUGGESTED_TIMES = ['5 min', '10 min', '15 min', '30 min', '1 hour', '2 hours', '4 hours', '8 hours', '12 hours',
                       '1 day', '2 days', '4 days', '1 week', '2 weeks', '1 month']

    class State(Enum):
        """States for the conversation."""
        CHOOSE_ALARM = 1
        CHOOSE_ACTION = 2
        CHOOSE_TIME = 3

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
        self.last_message = None

    def run_loop(self):
        """Run the main loop for the Telegram bot."""
        if not UI_TELEGRAM_BOT_TOKEN:
            print('Telegram bot token is not defined')
            return

        updater = Updater(token=UI_TELEGRAM_BOT_TOKEN)
        dispatcher = updater.dispatcher
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

        handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', self.command_start()),
                CommandHandler('overdue', self.command_overdue())
            ],
            states={
                self.State.CHOOSE_ALARM: [MessageHandler([Filters.text], self.show_alarm_details())],
                self.State.CHOOSE_ACTION: [RegexHandler(
                    '^({actions})$'.format(actions='|'.join(self.ACTION_BUTTONS)), self.execute_action())],
                self.State.CHOOSE_TIME: [MessageHandler([Filters.text], self.snooze_alarm())],
            },
            fallbacks=[CommandHandler('cancel', self.cancel())],
            allow_reentry=True
        )
        dispatcher.add_handler(handler)

        updater.start_polling()
        updater.idle()

    def send_message(self, text, reply_markup=None):
        """Send a message to the Telegram chat.

        :param text: Text to send.
        :param reply_markup: Optional buttons/markup to the chat.
        """
        self.bot.send_message(chat_id=self.update.message.chat_id, text=text, reply_markup=reply_markup)

    @staticmethod
    def arrange_keyboard(all_buttons: list, buttons_by_row: int) -> list:
        """Arrange a keyboard, splitting buttons into rows."""
        start = 0
        rows = []
        while start < len(all_buttons):
            rows.append(all_buttons[start:start + buttons_by_row])
            start += buttons_by_row
        return rows

    @bot_callback
    def command_start(self):
        """Start the bot with a friendly message."""
        self.send_message("I'm a bot to help you with your chores.")

    def show_overdue_alarms(self):
        """Show overdues alarms on a chat message."""
        right_now = datetime.now()
        # pylint: disable=no-member
        query = Alarm.query.filter(Alarm.current_state == AlarmState.UNSEEN,
                                   Alarm.next_at <= right_now).order_by(Alarm.next_at.desc())
        chores = []
        buttons = []
        for alarm in query.all():
            buttons.append('{}: {}'.format(alarm.id, alarm.chore.title[:30]))
            chores.append('\u2705 {}: {}'.format(alarm.id, alarm.one_line))

        if not chores:
            self.send_message('You have no overdue chores, congratulations! \U0001F44F\U0001F3FB')
        else:
            self.update.message.reply_text(
                'Those are your overdue chores:\n\n{chores}'.format(chores='\n'.join(chores)),
                reply_markup=ReplyKeyboardMarkup(self.arrange_keyboard(buttons, 2), one_time_keyboard=True,
                                                 resize_keyboard=True))

    @bot_callback
    def command_overdue(self):
        """Overdue chores, most recent first."""
        self.show_overdue_alarms()
        return self.State.CHOOSE_ALARM

    @bot_callback
    def show_alarm_details(self):
        """Show options for a chore."""
        self.last_alarm_id = int(self.text.split(':')[0])
        alarm = Alarm.query.get(self.last_alarm_id)  # pylint: disable=no-member
        self.update.message.reply_text(
            'What do you want to do with this alarm?\n{}'.format(alarm.one_line),
            reply_markup=ReplyKeyboardMarkup(self.arrange_keyboard(self.ACTION_BUTTONS, 3), one_time_keyboard=True,
                                             resize_keyboard=True))
        return self.State.CHOOSE_ACTION

    @bot_callback
    def execute_action(self):
        """Choose an action for the alarm."""
        function_map = {
            self.Actions.COMPLETE.value: (Alarm.complete, 'This occurrence is completed.'),
            self.Actions.SNOOZE.value: (Alarm.snooze, 'Alarm snoozed for'),
            self.Actions.SKIP.value: (Alarm.skip, 'Skipping this occurrence.'),
            self.Actions.STOP.value: (Alarm.stop, 'This chore is stopped for now (no more alarms).'),
        }
        tuple_value = function_map.get(self.text)
        if not tuple_value:
            self.update.message.reply_text(
                "I don't understand the action '{}'. Try one of the buttons below.".format(self.text))
            return self.State.CHOOSE_ACTION

        function, message = tuple_value
        if function == Alarm.snooze:
            self.last_message = message
            self.update.message.reply_text(
                'Choose a time from the suggestions below, or write the desired time',
                reply_markup=ReplyKeyboardMarkup(self.arrange_keyboard(self.SUGGESTED_TIMES, 5),
                                                 one_time_keyboard=True, resize_keyboard=True))
            return self.State.CHOOSE_TIME

        alarm = Alarm.query.get(self.last_alarm_id)  # pylint: disable=no-member
        function(alarm)
        self.update.message.reply_text('{}\n{}'.format(message, alarm.one_line))

        self.show_overdue_alarms()
        return self.State.CHOOSE_ALARM

    @bot_callback
    def snooze_alarm(self):
        """Snooze an alarm using the desired input time."""
        if not self.last_alarm_id:
            self.send_message('No alarm is selected, choose one below')
        else:
            alarm = Alarm.query.get(self.last_alarm_id)  # pylint: disable=no-member
            alarm.snooze(self.text)
            self.update.message.reply_text('{} {}\n{}'.format(self.last_message, self.text, alarm.one_line))

        self.show_overdue_alarms()
        return self.State.CHOOSE_ALARM

    @bot_callback
    def cancel(self):
        """Cancel the conversation."""
        user = self.update.message.from_user
        self.update.message.reply_text('Bye! I hope we can talk again some day, {}.'.format(user.first_name))
        return ConversationHandler.END
