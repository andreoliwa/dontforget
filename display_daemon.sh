#!/usr/bin/env bash
# For now, no cron jobs will be used.
# Execute this line to keep the daemon running:
# $ DONTFORGET_ENV=prod /path/to/python-dontforget/display_daemon.sh

# Use DONTFORGET_ENV=prod to point to the production database.

# To check if this script worked and manage.py is running, use this:
# ps aux | grep python-dontforget/manage.py

# Activate the "dontforget" virtual environment (which should exist in this machine).
source $(echo $VIRTUALENVWRAPPER_HOOK_DIR)/dontforget/bin/activate

# Run manage.py from this same directory.
$(dirname $0)/manage.py display -d &
