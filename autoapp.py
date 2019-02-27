"""Create an application instance."""
from prettyconf import config

from dontforget.app import create_app
from dontforget.settings import DevConfig, ProdConfig

CONFIG = DevConfig if config("FLASK_DEBUG", default=False, cast=config.boolean) else ProdConfig

app = create_app(CONFIG)
