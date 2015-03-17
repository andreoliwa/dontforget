Don't Forget
============

| |docs| |travis| |appveyor| |coveralls| |landscape| |scrutinizer|
| |version| |downloads| |wheel| |supported-versions| |supported-implementations|

.. |docs| image:: https://readthedocs.org/projects/dontforget/badge/?style=flat
    :target: https://readthedocs.org/projects/dontforget
    :alt: Documentation Status

.. |travis| image:: http://img.shields.io/travis/wagnerandreoli/dontforget/master.png?style=flat
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/wagnerandreoli/dontforget

.. |appveyor| image:: https://ci.appveyor.com/api/projects/status/github/wagnerandreoli/dontforget?branch=master
    :alt: AppVeyor Build Status
    :target: https://ci.appveyor.com/project/wagnerandreoli/dontforget

.. |coveralls| image:: http://img.shields.io/coveralls/wagnerandreoli/dontforget/master.png?style=flat
    :alt: Coverage Status
    :target: https://coveralls.io/r/wagnerandreoli/dontforget

.. |landscape| image:: https://landscape.io/github/wagnerandreoli/dontforget/master/landscape.svg?style=flat
    :target: https://landscape.io/github/wagnerandreoli/dontforget/master
    :alt: Code Quality Status

.. |version| image:: http://img.shields.io/pypi/v/dontforget.png?style=flat
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/dontforget

.. |downloads| image:: http://img.shields.io/pypi/dm/dontforget.png?style=flat
    :alt: PyPI Package monthly downloads
    :target: https://pypi.python.org/pypi/dontforget

.. |wheel| image:: https://pypip.in/wheel/dontforget/badge.png?style=flat
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/dontforget

.. |supported-versions| image:: https://pypip.in/py_versions/dontforget/badge.png?style=flat
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/dontforget

.. |supported-implementations| image:: https://pypip.in/implementation/dontforget/badge.png?style=flat
    :alt: Supported implementations
    :target: https://pypi.python.org/pypi/dontforget

.. |scrutinizer| image:: https://img.shields.io/scrutinizer/g/wagnerandreoli/dontforget/master.png?style=flat
    :alt: Scrutinizer Status
    :target: https://scrutinizer-ci.com/g/wagnerandreoli/dontforget/

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

* Free software: BSD license

Installation
============

::

    pip install dontforget

Documentation
=============

https://dontforget.readthedocs.org/

Development
===========

To run the all tests run::

    tox
