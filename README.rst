============
Don't Forget
============

|waffle| |travis| |coverage| |quantifiedcode|

.. |waffle| image:: https://badge.waffle.io/andreoliwa/python-dontforget.svg?label=ready&title=Ready
    :target: https://waffle.io/andreoliwa/python-dontforget
    :alt: 'Stories in Ready'

.. |travis| image:: https://travis-ci.org/andreoliwa/python-dontforget.svg
    :target: https://travis-ci.org/andreoliwa/python-dontforget/builds
    :alt: 'Travis Builds'

.. |coverage| image:: https://codecov.io/github/andreoliwa/python-dontforget/coverage.svg?branch=develop
    :target: https://codecov.io/github/andreoliwa/python-dontforget?branch=develop
    :alt: 'Coverage'

.. |quantifiedcode| image:: https://www.quantifiedcode.com/api/v1/project/5b4bdf674b4b4d7f853b2c840691ee0e/badge.svg
  :target: https://www.quantifiedcode.com/app/project/5b4bdf674b4b4d7f853b2c840691ee0e
  :alt: Code issues

A to-do list with repeating dates and reminders; you will never again forget to do something important.

The application consists of *chores* and *alarms* for them.

A *chore* can be anything you need to do, with or without due date, with or without repetition:

- a bill (recurring or one time);
- house chores you need to perform regularly;
- a personal identification document you have to renew (driver's license, passport);
- some food with its expiration date;
- a product you bought, with a due warranty period;
- some gig/concert/show you need to buy tickets to, before some time.

An *alarm* can be:

- set for any chore above, one of multiple times;
- snoozed: it will be shown again after the desired time, without changing the chore's status;
- skipped: the current iteration of the repeating chore will be marked as skipped;
- completed: the current iteration of the repeating chore will be marked as completed;
- finished: the whole series of repeating chores will be finished, and no more iterations will occur.


Quickstart
----------

First, set your app's secret key as an environment variable. For example, example add the following to ``.bashrc`` or ``.bash_profile``.

.. code-block:: bash

    export DONTFORGET_SECRET='something-really-secret'


Then run the following commands to bootstrap your environment.


::

    git clone https://github.com/andreoliwa/python-dontforget
    cd python-dontforget
    pip install -r requirements/dev.txt
    ./manage.py server

You will see a pretty welcome screen.

Once you have installed your DBMS, run the following to create your app's database tables and perform the initial migration:

::

    ./manage.py db init
    ./manage.py db migrate
    ./manage.py db upgrade
    ./manage.py server



Deployment
----------

In your production environment, make sure the ``DONTFORGET_ENV`` environment variable is set to ``"prod"``.


Shell
-----

To open the interactive shell, run ::

    ./manage.py shell

By default, you will have access to ``app``, ``db``, and the ``User`` model.


Running Tests
-------------

To run all tests, run ::

    ./manage.py test


Migrations
----------

Whenever a database migration needs to be made. Run the following commands:
::

    ./manage.py db migrate

This will generate a new migration script. Then run:
::

    ./manage.py db upgrade

To apply the migration.

For a full migration command reference, run ``./manage.py db --help``.
