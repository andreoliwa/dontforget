"""Telegram bot module."""
import logging
from datetime import datetime

import telegram
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

from dontforget.models import Alarm, AlarmState
from dontforget.settings import UI_TELEGRAM_BOT_TOKEN

BOT_APP = None


def show_dialog(alarm, **kwargs):
    """Show a dialog for an alarm using the Cocoa Dialog app.

    :param dontforget.models.Alarm alarm: The alarm to show.
    :return: A named tuple with the button and repetition that were selected.
    """
    print(alarm)
    # if 'bot' not in kwargs:
    #     return
    bot = kwargs.pop('bot')
    update = kwargs.pop('update')
    bot.sendMessage(chat_id=update.message.chat_id, text='Overdue alarm: {0}'.format(alarm))


def start(bot, update):
    """Start the bot."""
    bot.sendMessage(chat_id=update.message.chat_id, text="I'm a bot, please talk to me!")


def overdue(bot, update):
    """Overdue tasks."""
    right_now = datetime.now()
    with BOT_APP.app_context():
        # pylint: disable=no-member
        query = Alarm.query.filter(Alarm.current_state == AlarmState.UNSEEN,
                                   Alarm.next_at <= right_now).order_by(Alarm.id)
        all_alarms = [str(unseen_alarm) for unseen_alarm in query.all()]
        bot.sendMessage(chat_id=update.message.chat_id, text='Those are your overdue chores:\n{}'.format(
            '\n'.join(all_alarms)))


def echo(bot, update):
    """Echo a message."""
    bot.sendMessage(chat_id=update.message.chat_id, text='Current time: {0}, text received: {1}'.format(
        datetime.now().isoformat(), update.message.text))


def caps(bot, update, args):
    """Change text to uppercase."""
    text_caps = ' '.join(args).upper()
    bot.sendMessage(chat_id=update.message.chat_id, text=text_caps)


def unknown(bot, update):
    """Unknown command."""
    bot.sendMessage(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")


def task(bot, update):
    """Show options for a task."""
    custom_keyboard = [['Skip', 'Snooze'], ['Complete', 'Abort']]
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard)
    bot.sendMessage(chat_id=update.message.chat_id, text='What do you want to do with this task?',
                    reply_markup=reply_markup)


def run_loop(app):
    """Run the main loop for the Telegram bot."""
    global BOT_APP  # pylint: disable=global-statement
    BOT_APP = app

    if not UI_TELEGRAM_BOT_TOKEN:
        return

    updater = Updater(token=UI_TELEGRAM_BOT_TOKEN)
    dispatcher = updater.dispatcher
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    # TODO: Remove dummy commands
    handlers = (
        CommandHandler('start', start),
        MessageHandler([Filters.text], echo),
        CommandHandler('caps', caps, pass_args=True),
        CommandHandler('task', task),
        CommandHandler('overdue', overdue),
        # This one should always be the last one:
        MessageHandler([Filters.command], unknown),
    )
    for handler in handlers:
        dispatcher.add_handler(handler)

    updater.start_polling()
    updater.idle()
