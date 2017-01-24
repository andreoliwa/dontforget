"""Telegram bot module."""
from datetime import datetime
from enum import Enum

import maya
from telepot import DelegatorBot, glance
from telepot.delegate import create_open, pave_event_space, per_chat_id
from telepot.helper import ChatHandler
from telepot.namedtuple import ReplyKeyboardMarkup, ReplyKeyboardRemove

from dontforget.cron import spawn_alarms
from dontforget.extensions import db
from dontforget.models import Alarm, AlarmState, Chore
from dontforget.settings import UI_TELEGRAM_BOT_IDLE_TIMEOUT, UI_TELEGRAM_BOT_TOKEN


class ChoreBot(ChatHandler):  # pylint: disable=too-many-instance-attributes
    """Chat bot to handle chores."""

    class Step(Enum):
        """Steps for the conversation."""

        CHOOSE_ALARM = 1
        CHOOSE_ACTION = 2
        CHOOSE_TIME = 3

    class Actions(Enum):
        """Actions that can be performed on an alarm."""

        COMPLETE = 'Complete'
        SNOOZE = 'Snooze'
        SKIP = 'Jump'
        STOP = 'End series'

    ACTION_BUTTONS = [Actions.COMPLETE.value, Actions.SNOOZE.value, Actions.SKIP.value, Actions.STOP.value]
    SUGGESTED_TIMES = ['5 min', '10 min', '15 min', '30 min', '1 hour', '2 hours', '4 hours', '8 hours', '12 hours',
                       '1 day', '2 days', '4 days', '1 week', '2 weeks', '1 month']

    SEPARATORS = '\n,;'
    TRANSLATION_TABLE = str.maketrans(SEPARATORS, '|' * len(SEPARATORS))

    def __init__(self, *args, flask_app=None, **kwargs):
        """Init instance."""
        self.flask_app = flask_app
        """:type: flask.app.Flask"""

        self.next_step = None
        self.msg = None
        self.text = None
        """:type: str"""

        self.command = None
        """:type: str"""
        self.command_args = None
        """:type: str"""

        self.alarm_id = None
        """:type: int"""
        self.action_message = None

        super(ChoreBot, self).__init__(*args, **kwargs)

        # Alias to the sendMessage() function, also to avoid pylint annoying messages.
        self.send_message = self.sender.sendMessage   # pylint: disable=no-member

    def on_chat_message(self, msg):
        """Handle chat messages."""
        content_type, chat_type, chat_id = glance(msg)  # pylint: disable=unused-variable

        if content_type != 'text':
            self.send_message('I only understand text.')
            return

        self.msg = msg
        self.text = msg['text']
        """:type: str"""

        # Get the first command in the list of entities.
        self.command = None
        self.command_args = None
        if 'entities' in msg:
            self.command, self.command_args = min(
                [(self.text[entity['offset']:entity['length']], self.text[entity['length'] + 1:])
                 for entity in msg['entities'] if entity['type'] == 'bot_command'])

            # Set an explicit None in case the message only contains the command.
            if self.command == self.text:
                self.command_args = None

        mapping = {
            '/start': self.show_welcome_message,
            '/overdue': self.show_overdue_alarms,
            '/add': self.add_chore,
            self.Step.CHOOSE_ALARM: self.show_alarm_details,
            self.Step.CHOOSE_ACTION: self.execute_action,
            self.Step.CHOOSE_TIME: self.snooze_alarm,
        }
        function = None
        for value in (self.next_step, self.text, self.command):
            function = mapping.get(value)
            if function:
                break
        if not function:
            function = self.fallback_message

        with self.flask_app.app_context():
            self.next_step = function()

    def show_welcome_message(self):
        """Show a welcome message."""
        self.send_message("I'm a bot to help you with your chores.")
        # TODO test is broken
        # reply_markup=ReplyKeyboardRemove(remove_keyboard=True, selective=True)

    def fallback_message(self):
        """Show a fallback message in case of an unknown command or text."""
        self.send_message("I don't understand what you mean.")

    def show_overdue_alarms(self):
        """Show overdue alarms on a chat message."""
        right_now = datetime.utcnow()
        query = Alarm.query.filter(  # pylint: disable=no-member
            Alarm.current_state == AlarmState.UNSEEN, Alarm.next_at <= right_now).order_by(Alarm.next_at.desc())
        chores = []
        buttons = []
        for alarm in query.all():
            buttons.append('{}: {}'.format(alarm.id, alarm.chore.title[:30]))
            chores.append('\u2705 {}: {}'.format(alarm.id, alarm.one_line))

        if not chores:
            self.send_message('You have no overdue chores, congratulations! \U0001F44F\U0001F3FB')
            return

        self.send_message(
            'Those are your overdue chores:\n\n{chores}'.format(chores='\n'.join(chores)),
            reply_markup=self.arrange_keyboard(buttons, 2))
        return self.Step.CHOOSE_ALARM

    def show_alarm_details(self):
        """Show details of an alarm."""
        try:
            self.alarm_id = int(self.text.split(':')[0])
        except ValueError:
            self.send_message("This doesn't look like a chore to me.")
            return self.Step.CHOOSE_ALARM

        alarm = Alarm.query.get(self.alarm_id)  # pylint: disable=no-member
        self.send_message(
            'What do you want to do with this alarm?\n{}'.format(alarm.one_line),
            reply_markup=self.arrange_keyboard(self.ACTION_BUTTONS, 4))
        return self.Step.CHOOSE_ACTION

    @staticmethod
    def arrange_keyboard(all_buttons: list, buttons_by_row: int) -> list:
        """Arrange a keyboard, splitting buttons into rows."""
        start = 0
        rows = []
        while start < len(all_buttons):
            rows.append(all_buttons[start:start + buttons_by_row])
            start += buttons_by_row
        return ReplyKeyboardMarkup(keyboard=rows, one_time_keyboard=True, resize_keyboard=True)

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
            self.send_message(
                "I don't understand the action '{}'. Try one of the buttons below.".format(self.text))
            return self.Step.CHOOSE_ACTION

        function, message = tuple_value
        if function == Alarm.snooze:
            self.action_message = message
            self.send_message(
                'Choose a time from the suggestions below, or write the desired time',
                reply_markup=self.arrange_keyboard(self.SUGGESTED_TIMES, 5))
            return self.Step.CHOOSE_TIME

        alarm = Alarm.query.get(self.alarm_id)  # pylint: disable=no-member
        function(alarm)
        self.send_message('{}\n{}'.format(message, alarm.one_line))

        return self.show_overdue_alarms()

    def snooze_alarm(self):
        """Snooze an alarm using the desired input time."""
        if not self.alarm_id:
            self.send_message('No alarm is selected, choose one below')
        else:
            alarm = Alarm.query.get(self.alarm_id)  # pylint: disable=no-member
            alarm.snooze(self.text)
            self.send_message('{} {}\n{}'.format(self.action_message, self.text, alarm.one_line))

        self.show_overdue_alarms()

    def on__idle(self, event):
        """Close the conversation when idle for some time."""
        if self.next_step:
            self.send_message("It looks like you're busy now. Let's talk later, {}.".format(
                self.msg['from']['first_name']), reply_markup=ReplyKeyboardRemove(remove_keyboard=True, selective=True))
        self.close()  # pylint: disable=no-member

    def add_chore(self):
        """Add a chore."""
        args = []
        if self.command_args is not None:
            args += list(map(str.strip, self.command_args.translate(self.TRANSLATION_TABLE).split('|')))
        title, alarm_start, repetition = args + [None] * (3 - len(args))  # pylint: disable=unused-variable

        db.session.add(Chore(title=title, alarm_start=maya.when(alarm_start).datetime()))
        db.session.commit()
        spawn_alarms()

        self.send_message('The chore was added.')


def main_loop(app, queue=None):
    """Main loop of the bot.

    :param flask.app.Flask app: Flask app.
    :param queue: Update queue to be used as the source of updates instead of the Telegram API server. Used in tests.
    """
    bot = DelegatorBot(UI_TELEGRAM_BOT_TOKEN, [
        pave_event_space()(
            per_chat_id(), create_open, ChoreBot, timeout=UI_TELEGRAM_BOT_IDLE_TIMEOUT, flask_app=app),
    ])
    forever = False if queue else 'Listening...'
    bot.message_loop(source=queue, run_forever=forever)
