"""Telegram bot module."""
import re
from enum import Enum

import maya
from sqlalchemy import and_
from telepot import DelegatorBot, glance
from telepot.delegate import create_open, pave_event_space, per_chat_id
from telepot.helper import ChatHandler
from telepot.namedtuple import ReplyKeyboardMarkup, ReplyKeyboardRemove

from dontforget.app import db
from dontforget.cron import spawn_alarms
from dontforget.models import Alarm, AlarmState, Chore
from dontforget.repetition import right_now
from dontforget.settings import TELEGRAM_IDLE_TIMEOUT, TELEGRAM_TOKEN
from dontforget.utils import UT


class DispatchAgain(Exception):
    """Exception to force another message dispatch."""

    pass


class ChoreBot(ChatHandler):  # pylint: disable=too-many-instance-attributes
    """Chat bot to handle chores."""

    class Step(Enum):
        """Steps for the conversation."""

        CHOOSE_ACTION = 1
        CHOOSE_TIME = 2
        TYPE_CHORE_INFO = 3

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
        self.alarm = None
        self.action_message = None

        super(ChoreBot, self).__init__(*args, **kwargs)

        # Raw mapping with tuples when the same function has several shortcuts, plus help text when available.
        raw_mapping = {
            ('/start', '/help'): (self.show_help, 'this help'),
            ('/add', '/new'): (self.add_command, 'add a chore with an alarm'),
            ('/overdue', '/due'): (self.show_overdue_alarms, 'overdue alarms'),
            ('/chores', '/active'): (self.show_active_chores, 'chores with active alarms'),
            '/all': (self.show_all_chores, 'all chores'),
            '/id': self.show_alarm_details,
            self.Step.CHOOSE_ACTION: self.execute_action,
            self.Step.CHOOSE_TIME: self.snooze_alarm,
            self.Step.TYPE_CHORE_INFO: self.type_chore_info,
        }

        # Expand into a key/value mapping used by the bot.
        self.mapping = {}
        self.full_help = []
        for key_or_tuple, function_help in raw_mapping.items():
            if isinstance(function_help, tuple):
                function, help_text = function_help
            else:
                function = function_help
                help_text = None

            commands = []
            if isinstance(key_or_tuple, tuple):
                for key in key_or_tuple:
                    self.mapping[key] = function
                    commands.append(key)
            else:
                self.mapping[key_or_tuple] = function
                commands.append(key_or_tuple)

            if help_text:
                self.full_help.append('{commands} - {help_text}'.format(
                    commands=' or '.join(commands), help_text=help_text))

    def show_help(self):
        """Show a help message."""
        self.send_message(
            'I\'m a bot to help you with your chores.'
            '\nWhat you can do:'
            '\n{}'.format('\n'.join(self.full_help))
        )

    def send_message(self, *args, **kwargs):
        """Send a message, and remove the keyboard if none was sent.

        Also show a marker for debug purposes, when in the development environment.
        """
        reply_markup = kwargs.pop('reply_markup', ReplyKeyboardRemove(remove_keyboard=True, selective=True))
        kwargs['reply_markup'] = reply_markup

        if self.flask_app.config.get('ENV') != 'dev':
            return self.sender.sendMessage(*args, **kwargs)  # pylint: disable=no-member

        if 'text' in kwargs:
            text = kwargs.pop('text', '')
            remaining_args = args
        else:
            text = args[0]
            remaining_args = args[1:]
        text += ' (DEV)'
        return self.sender.sendMessage(*remaining_args, text=text, **kwargs)  # pylint: disable=no-member

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

            # Consider the underscore as a separator between a command and its arguments.
            if '_' in self.command:
                self.command, self.command_args = self.command.split('_', 1)

            # Set an explicit None in case the message only contains the command.
            if self.command == self.text:
                self.command_args = None

        # Loop until a message is processed.
        while True:
            try:
                # Try finding a valid function to process the message,
                # first matching the next step, then the text, then a command.
                function = None
                for value in (self.next_step, self.text, self.command):
                    function = self.mapping.get(value)
                    if function:
                        break

                # Fallback message, usually to warn the user that
                # the message was not understood.
                if not function:
                    function = self.fallback_message

                # Execute the function inside an app context,
                # and save the result as the next step in the conversation.
                with self.flask_app.app_context():
                    self.next_step = function()

                # Break when a message was successfully processed.
                break
            except DispatchAgain:
                # Reset the current step and try
                self.next_step = None

    def fallback_message(self):
        """Show a fallback message in case of an unknown command or text."""
        self.send_message("I don't understand what you mean.")

    def show_overdue_alarms(self):
        """Show overdue alarms on a chat message."""
        spawn_alarms()

        query = Alarm.query.filter(  # pylint: disable=no-member
            Alarm.current_state == AlarmState.UNSEEN, Alarm.next_at <= right_now()).order_by(Alarm.next_at.desc())
        chores = []
        for alarm in query.all():
            chores.append('\u2705 /id_{}: {}'.format(alarm.id, alarm.one_line))

        if not chores:
            self.send_message('You have no overdue chores, congratulations! \U0001F44F\U0001F3FB')
            return

        self.send_message('Those are your overdue chores:\n\n{chores}'.format(chores='\n'.join(chores)))

    def show_alarm_details(self):
        """Show details of an alarm."""
        self.alarm = None
        self.alarm_id = None
        if self.command_args:
            # Get only digits from the text.
            self.alarm_id = int(re.sub(r'\D', '', self.command_args))

            # Query the unseen alarm with this id.
            self.alarm = Alarm.query.filter_by(  # pylint: disable=no-member
                id=self.alarm_id, current_state=AlarmState.UNSEEN).first()
        if not self.alarm:
            self.send_message('I could not find this alarm')
            return

        self.send_message(
            'What do you want to do with this alarm?\n{}'.format(self.alarm.one_line),
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
            raise DispatchAgain

        function, message = tuple_value
        if function == Alarm.snooze:
            self.action_message = message
            self.send_message(
                'Choose a time from the suggestions below, or write the desired time',
                reply_markup=self.arrange_keyboard(self.SUGGESTED_TIMES, 4))
            return self.Step.CHOOSE_TIME

        function(self.alarm)
        self.send_message('{}\n{}'.format(message, self.alarm.one_line))

        return self.show_overdue_alarms()

    def snooze_alarm(self):
        """Snooze an alarm using the desired input time."""
        if not self.alarm:
            self.send_message('No alarm is selected, choose one below')
        elif not self.action_message:
            self.send_message('No action was selected')
        else:
            self.alarm.snooze(self.text)
            self.send_message('{} {}\n{}'.format(self.action_message, self.text, self.alarm.one_line))

        self.show_overdue_alarms()

    def on__idle(self, event):
        """Close the conversation when idle for some time."""
        self.close()  # pylint: disable=no-member

    def add_command(self):
        """Add a chore."""
        if self.command_args is None:
            self.send_message('To add a new chore, enter the following info (one per line or comma separated):\n'
                              '\u2022 Title\n'
                              '\u2022 (optional) First alarm. E.g.: today 10am, tomorrow 9pm, 20 Jan 2017...\n'
                              '\u2022 (optional) Repetition. E.g.: once, weekly, every 3 days...\n'
                              'Or choose /cancel to stop adding a new chore.')
            return self.Step.TYPE_CHORE_INFO

        self._parse_chore_info(self.command_args)

    def type_chore_info(self):
        """Accept the chore info typed by the user."""
        self._parse_chore_info(self.text)

    def _parse_chore_info(self, info: str):
        """Parse chore info from the message."""
        if self.command == '/cancel':
            self.send_message('Okay, no new chore then.')
            return

        args = list(map(str.strip, info.translate(self.TRANSLATION_TABLE).split('|')))
        arg_title, arg_alarm_start, arg_repetition = args + [None] * (3 - len(args))

        fields = dict(
            title=arg_title,
            alarm_start=(maya.when(arg_alarm_start) if arg_alarm_start else maya.now()).datetime(),
            repetition=arg_repetition,
        )
        db.session.add(Chore(**fields))
        db.session.commit()

        self.send_message('The chore was added.')

    def show_active_chores(self):
        """Show only active chores."""
        return self._show_chores(Chore.query.join)  # pylint: disable=no-member

    def show_all_chores(self):
        """Show all chores."""
        return self._show_chores(Chore.query.outerjoin)  # pylint: disable=no-member

    def _show_chores(self, join_function):
        """Show chores using the desired JOIN function."""
        query = join_function(
            Alarm, and_(Alarm.chore_id == Chore.id, Alarm.current_state == AlarmState.UNSEEN)).order_by(
                Alarm.updated_at.desc(), Chore.id.desc()).with_entities(Chore, Alarm.current_state)
        chores = []
        for row in query.all():
            chores.append('{active} {one_line}'.format(
                active=UT.LargeBlueCircle if row.current_state else UT.LargeRedCircle,
                one_line=row.Chore.one_line
            ))
        if not chores:
            self.send_message("You don't have any chores yet, use /add to create one")
            return

        self.send_message('\n{chores}'.format(chores='\n'.join(chores)))


def main_loop(app, queue=None):
    """Main loop of the bot.

    :param flask.app.Flask app: Flask app.
    :param queue: Update queue to be used as the source of updates instead of the Telegram API server. Used in tests.
    """
    bot = DelegatorBot(TELEGRAM_TOKEN, [
        pave_event_space()(
            per_chat_id(), create_open, ChoreBot, timeout=TELEGRAM_IDLE_TIMEOUT, flask_app=app),
    ])
    forever = False if queue else 'Listening ({})...'.format(app.config['ENV'])
    bot.message_loop(source=queue, run_forever=forever)
