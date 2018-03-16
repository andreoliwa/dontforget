"""Application menu at the status bar."""
import plistlib
from random import choice

import objc
from AppKit import NSApplication, NSEventTrackingRunLoopMode, NSMenu, NSMenuItem, NSStatusBar
from Foundation import NSRunLoop, NSTimer

from dontforget.utils import UT


def suppress_dock_icon():
    """Don't show the dock icon for the app."""
    path_to_current_bundle = objc.currentBundle().bundlePath()
    path_to_plist = '{}/Contents/Info.plist'.format(path_to_current_bundle)
    plist = plistlib.readPlist(path_to_plist)
    plist['LSUIElement'] = '1'
    plistlib.writePlist(plist, path_to_plist)
    print('Done! Run Sentinel again.')


class Sentinel(NSApplication):
    """Application with a menu and a timer, to monitor activities.

    Heavily inspired by the Simon app, thanks a lot!
    https://github.com/half0wl/simon.
    """

    def finishLaunching(self):
        """Setup the menu and run the app loop."""
        self._setup_menu_bar()

        # Create a timer which fires the update_ method every 1second,
        # and add it to the runloop
        NSRunLoop.currentRunLoop().addTimer_forMode_(
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                1, self, 'update:', '', True
            ),
            NSEventTrackingRunLoopMode
        )

        print('Sentinel is now running.')
        print('CTRL+C does not work here.')
        print('You can quit through the menu bar (Sentinel -> Quit).')

    def update_(self, timer):
        """Run the update on every cycle of the timer."""
        # FIXME: Replace this random update with something not distracting.
        self.main_menu.setTitle_('{icon} {count}'.format(
            icon=choice([UT.FourLeafClover, UT.Fire, UT.LargeRedCircle, UT.LargeBlueCircle]),
            count=choice(range(1, 50))
        ))

    def _setup_menu_bar(self):
        """Setup the menu bar of the app."""
        self.main_menu = NSStatusBar.systemStatusBar().statusItemWithLength_(-1)
        self.menuBar = NSMenu.alloc().init()

        # [f for f in dir(NSButton) if 'Title' in f]
        self.button = self.main_menu.button
        self.main_menu.setTitle_('\U0001F534 3')

        # Menu items
        quit_menu = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Quit', 'terminate:', '')

        # Add items to the menuBar
        self.menuBar.addItem_(quit_menu)

        # Add menu to status bar
        self.main_menu.setMenu_(self.menuBar)

    def _create_empty_menu_item(self):
        """Create an empty menu item."""
        return NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('', '', '')

    def doNothing_(self, sender):
        """Hack to enable menuItems by passing them this method as action.

        setEnabled_ isn't working, so this should do for now (achieves the same thing).
        """
        pass
