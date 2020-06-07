"""Application menu at the status bar."""
from datetime import datetime

import rumps
from apscheduler.schedulers.background import BackgroundScheduler

from dontforget.generic import UT


def tick():  # FIXME: this is only a test. Replace this by something useful
    """Display the current time."""
    rumps.notification("Tick", "Toc", "The time is: %s" % datetime.now())


class DontForgetApp(rumps.App):
    """The application."""

    def __init__(self):
        super(DontForgetApp, self).__init__(UT.ReminderRibbon)

    @staticmethod
    def start_scheduler():
        """Start the scheduler."""
        scheduler = BackgroundScheduler()
        scheduler.add_job(tick, "interval", seconds=10)
        scheduler.start()


def main():
    """Main function."""
    app = DontForgetApp()
    app.start_scheduler()
    app.run()
