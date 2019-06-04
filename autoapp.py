# -*- coding: utf-8 -*-
"""Create an application instance."""
from dontforget.app import create_app
from dontforget.constants import DEVELOPMENT
from dontforget.settings import FLASK_ENV, DevConfig, ProdConfig

CONFIG = DevConfig if FLASK_ENV == DEVELOPMENT else ProdConfig

app = create_app(CONFIG)
