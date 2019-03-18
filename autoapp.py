"""Create an application instance."""
from dontforget.app import create_app
from dontforget.config import FLASK_ENV, DevConfig, ProdConfig
from dontforget.constants import DEVELOPMENT

CONFIG = DevConfig if FLASK_ENV == DEVELOPMENT else ProdConfig

app = create_app(CONFIG)
