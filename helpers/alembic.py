# -*- coding: utf-8 -*-
# pylint: disable=no-member
"""Helpers for Alembic migrations."""
from functools import partial

import sqlalchemy as sa
from alembic import op


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

    if batch_operation:
        add_column = batch_operation.add_column
        execute = batch_operation.execute
        alter_column = batch_operation.alter_column
    else:
        add_column = partial(op.add_column, table_name)
        execute = op.execute
        alter_column = partial(op.alter_column, table_name)

    if not column_exists:
        add_column(sa.Column(column_name, column_type, nullable=True))
    if not batch_operation:
        execute('UPDATE "{}" SET "{}" = {}'.format(table_name, column_name, default_value))
    alter_column(column_name, nullable=False)
