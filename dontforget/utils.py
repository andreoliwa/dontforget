# -*- coding: utf-8 -*-
"""Helper utilities and decorators."""
from functools import partial

import sqlalchemy as sa
from alembic import op
from flask import flash

DATETIME_FORMAT = 'ddd MMM DD, YYYY HH:mm'
TIMEZONE = 'Europe/Berlin'


class UT:
    """Unicode table helper."""

    LargeRedCircle = '\U0001F534'
    LargeBlueCircle = '\U0001F535'


def flash_errors(form, category='warning'):
    """Flash all errors for a form."""
    for field, errors in form.errors.items():
        for error in errors:
            flash('{0} - {1}'.format(getattr(form, field).label.text, error), category)


def add_required_column(  # pylint: disable=too-many-arguments
        table_name, column_name, column_type, default_value=None, column_exists=False, batch_operation=None):
    """Add a required column to a table.

    NOT NULL fields must be populated with some value before setting `nullable=False`.

    :param str table_name: Name of the table.
    :param str column_name: Name of the column.
    :param column_type: Type of the column. E.g.: sa.String().
    :param default_value: The default value to be UPDATEd in the column. If not informed, then generates UUIDs.
    :param column_exists: Flag to indicate if the column already exists (to skip creation).
    """
    if default_value is None:
        default_value = 'uuid_generate_v4()'

    # pylint: disable=no-member
    if batch_operation:
        add_column = batch_operation.add_column
        execute = batch_operation.execute
        alter_column = batch_operation.alter_column
        table_name = batch_operation.impl.table_name
    else:
        add_column = partial(op.add_column, table_name)
        execute = op.execute
        alter_column = partial(op.alter_column, table_name)

    if not column_exists:
        add_column(sa.Column(column_name, column_type, nullable=True))
    if not batch_operation:
        execute('UPDATE "{0}" SET "{1}" = {2}'.format(table_name, column_name, default_value))
    alter_column(column_name, nullable=False)
