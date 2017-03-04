# -*- coding: utf-8 -*-
"""Database module, including the SQLAlchemy database object and DB-related utilities."""
import os
import sys

from alembic import op
from flask import current_app, has_app_context
from flask_migrate import Migrate, upgrade
from sqlalchemy import Column, ForeignKeyConstraint, MetaData, Table, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import reflection
from sqlalchemy.sql.ddl import DropConstraint, DropTable

from dontforget.settings import TestConfig
from dontforget.utils import to_list

from .app import db

# A list of tables that should be ignored when dropping and listing all our tables.
IGNORED_TABLES = ['spatial_ref_sys']


class CRUDMixin(object):
    """Mixin that adds convenience methods for CRUD (create, read, update, delete) operations."""

    @classmethod
    def create(cls, commit=True, **kwargs):
        """Create a new record and save it the database."""
        instance = cls(**kwargs)
        return instance.save(commit=commit)

    def update(self, commit=True, **kwargs):
        """Update specific fields of a record."""
        for attr, value in kwargs.items():
            setattr(self, attr, value)
        return self.save(commit=commit)

    def save(self, commit=True):
        """Save the record."""
        db.session.add(self)
        if commit:
            db.session.commit()
        return self

    def delete(self, commit=True):
        """Remove the record from the database."""
        db.session.delete(self)
        return commit and db.session.commit()


class Model(CRUDMixin, db.Model):
    """Base model class that includes CRUD convenience methods."""

    __abstract__ = True


# From Mike Bayer's "Building the app" talk
# https://speakerdeck.com/zzzeek/building-the-app
class SurrogatePK(object):
    """A mixin that adds a surrogate integer 'primary key' column named ``id`` to any declarative-mapped class."""

    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)

    @classmethod
    def get_by_id(cls, record_id):
        """Get record by ID."""
        if any(
                (isinstance(record_id, (str, bytes)) and record_id.isdigit(),
                 isinstance(record_id, (int, float))),
        ):
            return cls.query.get(int(record_id))  # pylint: disable=no-member
        return None


class CreatedUpdatedMixin(object):
    """A mixin that adds created and updated dates to a model."""

    # func.now() is equivalent to CURRENT_TIMESTAMP in SQLite, which is always UTC (GMT).
    # See https://www.sqlite.org/lang_datefunc.html
    created_at = db.Column(db.TIMESTAMP(timezone=True), nullable=False, default=func.now())
    updated_at = db.Column(db.TIMESTAMP(timezone=True), nullable=False, onupdate=func.now(), default=func.now())


def reference_col(tablename, nullable=False, pk_name='id', **kwargs):
    """Column that adds primary key foreign key reference.

    Usage: ::

        category_id = reference_col('category')
        category = relationship('Category', backref='categories')
    """
    return db.Column(
        db.ForeignKey('{0}.{1}'.format(tablename, pk_name)),
        nullable=nullable, **kwargs)


def db_refresh(short=False):
    """Refresh the database.

    :param short: Short version
    """
    create_local_context = not has_app_context()
    if create_local_context:
        # When this command is run from the command line, there is no app context, so let's create one
        from dontforget.app import create_app
        app_ = create_app(TestConfig)
        Migrate(app_, db, os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', '..', 'migrations'))
        context = app_.app_context()
        context.push()

    tmp_handlers = current_app.logger.handlers
    current_app.logger.handlers = []
    tmp_stderr = sys.stderr
    if short:
        sys.stderr = None

    db.reflect()
    drop_everything()
    upgrade()

    if short:
        sys.stderr = tmp_stderr

    current_app.logger.handlers = tmp_handlers

    if create_local_context:
        # Remove the context after use
        db.session.remove()
        context.pop()


def drop_everything():
    """Drop all constraints, then all tables.

    Adapted from:
    http://www.mbeckler.org/blog/?p=218
    https://bitbucket.org/zzzeek/sqlalchemy/wiki/UsageRecipes/DropEverything

    Using the ``db.drop_all()`` function can throw an error like this:
        sqlalchemy.exc.InternalError: (InternalError) cannot drop table voucher because other objects depend on it
        DETAIL:  constraint voucher_user_fk on table "user" depends on table voucher
        HINT:  Use DROP ... CASCADE to drop the dependent objects too.
        'DROP TABLE voucher' {}

    :return:
    """
    conn = db.engine.connect()

    # The transaction only applies if the DB supports transactional DDL, i.e. PostgreSQL, MS SQL Server
    trans = conn.begin()

    inspector = reflection.Inspector.from_engine(db.engine)

    # Gather all data first before dropping anything. Some DBs lock after things have been dropped in a transaction.
    metadata = MetaData()

    all_tables = []
    all_foreign_keys = []

    for table_name in inspector.get_table_names():
        if table_name in IGNORED_TABLES:
            continue

        foreign_keys = []
        for foreign_key in inspector.get_foreign_keys(table_name):
            if not foreign_key['name']:
                continue
            foreign_keys.append(ForeignKeyConstraint((), (), name=foreign_key['name']))
        table = Table(table_name, metadata, *foreign_keys)
        all_tables.append(table)
        all_foreign_keys.extend(foreign_keys)

    for foreign_key_constraint in all_foreign_keys:
        conn.execute(DropConstraint(foreign_key_constraint))

    for table in all_tables:
        conn.execute(DropTable(table))

    trans.commit()


def add_required_column(table_name, column_name, column_type,  # pylint: disable=too-many-arguments
                        default_value=None, column_exists=False, update_only_null=False):
    """Add a required column to a table.

    NOT NULL fields must be populated with some value before setting `nullable=False`.

    :param table_name: Name of the table.
    :type table_name: str

    :param column_name: Name of the column.
    :type column_name: str

    :param column_type: Type of the column. E.g.: sa.String().

    :param default_value: The default value to be UPDATEd in the column. If not informed, then generates UUIDs.

    :param column_exists: Flag to indicate if the column already exists (to skip creation).

    :param update_only_null: Flag to only update values that are null and leave the others
    """
    if default_value is None:
        default_value = 'uuid_generate_v4()'

    # pylint: disable=no-member
    if not column_exists:
        op.add_column(table_name, Column(column_name, column_type, nullable=True))

    query = 'UPDATE "{table}" SET "{column}" = {value}'
    if update_only_null:
        query = 'UPDATE "{table}" SET "{column}" = {value} WHERE "{column}" IS NULL'

    op.execute(query.format(table=table_name, column=column_name, value=default_value))
    op.alter_column(table_name, column_name, nullable=False)


def rename_postgresql_type(old_name, new_name):
    """Rename a type in PostgreSQL, but only if it does not already exist.

    This is useful for ENUMs, and to make them work with the cave_test database,
    which is not always recreated on each run (it depends on the SKIP_DB_CREATION environment variable).

    :param old_name: Old type name.
    :param new_name: New type name.
    """
    # pylint: disable=no-member
    connection = op.get_bind()
    result = connection.execute("SELECT COUNT(0) FROM pg_type WHERE typname = '{}'".format(new_name)).fetchall()
    if result[0][0] == 0:
        op.execute('ALTER TYPE {} RENAME TO {}'.format(old_name, new_name))


def change_enum(enum_name, old_options, new_options, affected_tables_columns):
    """Alter ENUM.

    :param enum_name: Name of the enum
    :param old_options: Tuple of old options to add
    :param new_options: Tuple of new options to add
    :param dict affected_tables_columns: Tables and columns using this enum.
        Dictionary with table name as key and column names (list or string) as values.
    """
    # pylint: disable=no-member
    old_type = postgresql.ENUM(*old_options, name=enum_name, create_type=False)
    new_type = postgresql.ENUM(*new_options, name=enum_name, create_type=False)
    tmp_name = '_{}'.format(enum_name)
    tmp_type = postgresql.ENUM(*new_options, name=tmp_name, create_type=False)

    # Create a new temporary enum, alter all tables using the old enum, and then drop the temporary enum.
    tmp_type.create(op.get_bind(), checkfirst=False)
    for affected_table, affected_columns in affected_tables_columns.items():
        for affected_column in to_list(affected_columns):
            op.execute('ALTER TABLE {affected_table} ALTER COLUMN {affected_column} TYPE {tmp_name} '
                       'USING {enum_name}::text::{tmp_name}'
                       .format(affected_table=affected_table, affected_column=affected_column,
                               enum_name=enum_name, tmp_name=tmp_name))
    old_type.drop(op.get_bind())

    # Create the new final enum and adjust all tables.
    new_type.create(op.get_bind(), checkfirst=False)
    for affected_table, affected_columns in affected_tables_columns.items():
        for affected_column in to_list(affected_columns):
            op.execute('ALTER TABLE {affected_table} ALTER COLUMN {affected_column} TYPE {enum_name} '
                       'USING {enum_name}::text::{enum_name}'.
                       format(affected_table=affected_table, affected_column=affected_column, enum_name=enum_name))
    tmp_type.drop(op.get_bind())
