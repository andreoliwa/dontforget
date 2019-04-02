# -*- coding: utf-8 -*-
"""The app module, containing the app factory function."""
from flask import Flask, render_template
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from dontforget import commands
from dontforget.settings import ProdConfig
from dontforget.views import blueprint

db = SQLAlchemy()
migrate = Migrate()  # pylint: disable=invalid-name


def create_app(config_object=ProdConfig):
    """An application factory, as explained here: http://flask.pocoo.org/docs/patterns/appfactories/.

    :param config_object: The configuration object to use.
    """
    app = Flask(__name__)
    app.config.from_object(config_object)
    register_blueprints(app)
    register_extensions(app)
    # TODO: feat: add missing favicon
    # register_errorhandlers(app)
    register_commands(app)
    return app


def register_blueprints(app):
    """Register Flask blueprints."""
    app.register_blueprint(blueprint)


def register_extensions(app):
    """Register Flask extensions."""
    db.init_app(app)
    migrate.init_app(app, db)
    return None


def register_errorhandlers(app):
    """Register error handlers."""

    def render_error(error):
        """Render error template."""
        # If a HTTPException, pull the `code` attribute; default to 500
        error_code = getattr(error, "code", 500)
        # TODO: fix: error templates
        return render_template("{0}.html".format(error_code)), error_code

    for errcode in [401, 404, 500]:
        app.errorhandler(errcode)(render_error)
    return None


def register_commands(app):
    """Register Click commands."""
    app.cli.add_command(commands.desktop)
    app.cli.add_command(commands.db_refresh)
    app.cli.add_command(commands.telegram)
    app.cli.add_command(commands.go_home)
