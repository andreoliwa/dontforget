"""Main application package."""

import warnings

# TODO Safely ignore apscheduler warnings. This should be fixed when version 4.x is released.
#  https://github.com/agronholm/apscheduler/discussions/570#discussioncomment-1562516
#  apscheduler/util.py:95: PytzUsageWarning: The zone attribute is specific to pytz's interface; please migrate to
#  a new time zone provider. For more details on how to do so,
#  see https://pytz-deprecation-shim.readthedocs.io/en/latest/migration.html
#  apscheduler/util.py:166: PytzUsageWarning: The localize method is no longer necessary, as this time zone supports
#  the fold attribute (PEP 495). For more details on migrating to a PEP 495-compliant implementation,
#  see https://pytz-deprecation-shim.readthedocs.io/en/latest/migration.html
#  apscheduler/triggers/interval.py:66: PytzUsageWarning: The normalize method is no longer necessary, as this time
#  zone supports the fold attribute (PEP 495). For more details on migrating to a PEP 495-compliant implementation,
#  see https://pytz-deprecation-shim.readthedocs.io/en/latest/migration.html
warnings.filterwarnings(action="ignore", module="apscheduler")
