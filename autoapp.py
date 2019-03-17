"""Create an application instance."""
from dontforget.app import create_app
from dontforget.config import FLASK_DEBUG, DevConfig, ProdConfig

CONFIG = DevConfig if FLASK_DEBUG else ProdConfig

app = create_app(CONFIG)
