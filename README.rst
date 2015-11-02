============
Don't Forget
============

A to-do list with recurring dates and reminders, so you never again will forget to do something important.

The application consists of *tasks* and *reminders* for them.

A *task* can be anything you need to do, with or without due date, with or without repetition:
- a bill (recurring or one time);
- house chores you need to perform regularly;
- a personal identification document you have to renew (driver's license, passport);
- some food with its expiration date;
- a product you bought, with a due warranty period;
- some gig/concert/show you need to buy tickets to, before some time.

You can create your custom types of task, and define default reminders and snooze times for each type.

A *reminder* can be:
- set for any task above, one of multiple times;
- snoozed: it will be shown again after the desired time, without changing the task's status;
- skipped: the current iteration of the repeating task will be marked as skipped;
- completed: the current iteration of the repeating task will be marked as completed;
- finished: the whole series of repeating tasks will be finished, and no more iterations will occur.


Quickstart
----------

First, set your app's secret key as an environment variable. For example, example add the following to ``.bashrc`` or ``.bash_profile``.

.. code-block:: bash

    export DONTFORGET_SECRET='something-really-secret'


Then run the following commands to bootstrap your environment.


::

    git clone https://github.com/andreoliw/dontforget
    cd dontforget
    pip install -r requirements/dev.txt
    python manage.py server

You will see a pretty welcome screen.

Once you have installed your DBMS, run the following to create your app's database tables and perform the initial migration:

::

    python manage.py db init
    python manage.py db migrate
    python manage.py db upgrade
    python manage.py server



Deployment
----------

In your production environment, make sure the ``DONTFORGET_ENV`` environment variable is set to ``"prod"``.


Shell
-----

To open the interactive shell, run ::

    python manage.py shell

By default, you will have access to ``app``, ``db``, and the ``User`` model.


Running Tests
-------------

To run all tests, run ::

    python manage.py test


Migrations
----------

Whenever a database migration needs to be made. Run the following commands:
::

    python manage.py db migrate

This will generate a new migration script. Then run:
::

    python manage.py db upgrade

To apply the migration.

For a full migration command reference, run ``python manage.py db --help``.
