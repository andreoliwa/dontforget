"""Telegram bot module."""
# pylint: disable=no-self-use
import logging
from datetime import datetime

import telegram
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

from dontforget.models import Alarm, AlarmState
from dontforget.settings import UI_TELEGRAM_BOT_TOKEN


class TelegramBot:
    """Telegram bot to answer commands."""

    def __init__(self, app):
        self.app = app

    def start(self):
        """Start the bot."""
        def callback(bot, update):
            """Function called by the bot when there is an update."""
            bot.sendMessage(chat_id=update.message.chat_id, text="I'm a bot, please talk to me?")
        return callback

    def echo(self):
        """Echo a message."""
        def callback(bot, update):
            """Function called by the bot when there is an update."""
            bot.sendMessage(chat_id=update.message.chat_id, text='Current time: {0}, text received: {1}'.format(
                datetime.now().isoformat(), update.message.text))
        return callback

    def caps(self):
        """Change text to uppercase."""
        def callback(bot, update, args):
            """Function called by the bot when there is an update."""
            text_caps = ' '.join(args).upper()
            bot.sendMessage(chat_id=update.message.chat_id, text=text_caps)
        return callback

    def chore(self):
        """Show options for a chore."""
        def callback(bot, update):
            """Function called by the bot when there is an update."""
            custom_keyboard = [['Skip', 'Snooze'], ['Complete', 'Abort']]
            reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard)
            bot.sendMessage(chat_id=update.message.chat_id, text='What do you want to do with this chore?',
                            reply_markup=reply_markup)
        return callback

    def overdue(self):
        """Overdue tasks."""
        def callback(bot, update):
            """Function called by the bot when there is an update."""
            right_now = datetime.now()
            with self.app.app_context():
                # pylint: disable=no-member
                query = Alarm.query.filter(Alarm.current_state == AlarmState.UNSEEN,
                                           Alarm.next_at <= right_now).order_by(Alarm.id)
                all_alarms = [str(unseen_alarm) for unseen_alarm in query.all()]
                bot.sendMessage(chat_id=update.message.chat_id, text='Those are your overdue chores:\n{}'.format(
                    '\n'.join(all_alarms)))
        return callback

    def unknown(self):
        """Unknown command."""
        def callback(bot, update):
            """Function called by the bot when there is an update."""
            bot.sendMessage(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")
        return callback

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
