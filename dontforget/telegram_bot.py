"""Telegram bot module."""
import re
from enum import Enum

import maya
from telepot import DelegatorBot, glance
from telepot.delegate import create_open, pave_event_space, per_chat_id
from telepot.helper import ChatHandler
from telepot.namedtuple import ReplyKeyboardMarkup, ReplyKeyboardRemove

from dontforget.app import db
from dontforget.models import AlarmAction, Chore
from dontforget.repetition import local_right_now
from dontforget.settings import TELEGRAM_IDLE_TIMEOUT, TELEGRAM_TOKEN
from dontforget.utils import DATETIME_FORMAT


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

    ACTION_BUTTONS = [action.capitalize() for action in (
        AlarmAction.COMPLETE, AlarmAction.SNOOZE, AlarmAction.JUMP, AlarmAction.PAUSE)]
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

        self.chore_id = None
        """:type: int"""
        self.chore = None
        self.action_message = None

        super(ChoreBot, self).__init__(*args, **kwargs)

        # Raw mapping with tuples when the same function has several shortcuts, plus help text when available.
        raw_mapping = {
            ('/start', '/help'): (self.show_help, 'this help'),
            ('/add', '/new'): (self.add_command, 'add a chore'),
            ('/overdue', '/due'): (self.show_overdue, 'overdue chores'),
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
        return self.sender.sendMessage(*remaining_args, text='(DEV) ' + text, **kwargs)  # pylint: disable=no-member

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
                (self.text[entity['offset']:entity['length']], self.text[entity['length'] + 1:])
                for entity in msg['entities'] if entity['type'] == 'bot_command')

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

    def show_overdue(self):
        """Show overdue alarms on a chat message."""
        chores = [chore.one_line for chore in Chore.query_overdue().all()]
        if not chores:
            self.send_message('You have no overdue chores, congratulations! \U0001F44F\U0001F3FB')
            return

        self.send_message('Your overdue chores at {date}:\n\n{chores}'.format(
            date=local_right_now().format(DATETIME_FORMAT), chores='\n'.join(chores)))

    def show_alarm_details(self):
        """Show details of an alarm."""
        self.chore = None
        self.chore_id = None
        if self.command_args:
            # Get only digits from the text.
            self.chore_id = int(re.sub(r'\D', '', self.command_args))
            self.chore = Chore.query.get(self.chore_id)  # pylint: disable=no-member
        if not self.chore:
            self.send_message('I could not find this chore')
            return

        self.send_message(
            'What do you want to do with this chore?\n{}'.format(self.chore.one_line),
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
            AlarmAction.COMPLETE: (Chore.complete, 'This occurrence is completed.'),
            AlarmAction.SNOOZE: (Chore.snooze, 'Alarm snoozed for'),
            AlarmAction.JUMP: (Chore.jump, 'Jumping this occurrence.'),
            AlarmAction.PAUSE: (Chore.pause, 'This chore is paused for now (no more alarms).'),
        }
        tuple_value = function_map.get(self.text.lower())
        if not tuple_value:
            raise DispatchAgain

        function, message = tuple_value
        if function == Chore.snooze:
            self.action_message = message
            self.send_message(
                'Choose a time from the suggestions below, or write the desired time',
                reply_markup=self.arrange_keyboard(self.SUGGESTED_TIMES, 4))
            return self.Step.CHOOSE_TIME

        function(self.chore)
        self.send_message('{}\n{}'.format(message, self.chore.one_line))

        return self.show_overdue()

    def snooze_alarm(self):
        """Snooze an alarm using the desired input time."""
        if not self.chore:
            self.send_message('No chore is selected, choose one below')
        elif not self.action_message:
            self.send_message('No action was selected')
        else:
            self.chore.snooze(self.text)
            self.send_message('{} {}\n{}'.format(self.action_message, self.text, self.chore.one_line))

        self.show_overdue()

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
        arg_title, arg_due_at, arg_repetition = args + [None] * (3 - len(args))  # type: ignore

        alarm_at = (maya.when(arg_due_at) if arg_due_at else maya.now()).datetime()
        fields = {'title': arg_title, 'due_at': alarm_at, 'alarm_at': alarm_at, 'repetition': arg_repetition}
        db.session.add(Chore(**fields))
        db.session.commit()

        self.send_message('The chore was added.')

    def show_active_chores(self):
        """Show only active chores."""
        # pylint: disable=no-member
        return self._show_chores(
            'Your active chores at {}:'.format(local_right_now().format(DATETIME_FORMAT)),
            Chore.query_active())

    def show_all_chores(self):
        """Show all chores."""
        # pylint: disable=no-member
        return self._show_chores(
            'Your chores at {}:'.format(local_right_now().format(DATETIME_FORMAT)),
            Chore.query)

    def _show_chores(self, message, base_query):
        """Show chores using the desired JOIN function."""
        query = base_query.order_by(Chore.updated_at.desc(), Chore.id.desc())
        chores = [chore.one_line for chore in query.all()]
        if not chores:
            self.send_message("You don't have any chores yet, use /add to create one")
            return

        self.send_message('{msg}\n{chores}'.format(msg=message, chores='\n'.join(chores)))


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
