"""Application menu at the status bar."""
import rumps

from dontforget.generic import UT


class DontForgetApp(rumps.App):
    """The application."""

    def __init__(self):
        super(DontForgetApp, self).__init__(UT.ReminderRibbon)


def main():
    """Main function."""
    rumps.debug_mode(True)  # TODO: Remove this once the menu is complete, or use an env variable
    DontForgetApp().run()
