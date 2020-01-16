"""Public section, including homepage and signup."""
from flask import Blueprint, jsonify

from dontforget.settings import FLASK_ENV

blueprint = Blueprint("public", __name__, static_folder="../static")


@blueprint.route("/", methods=["GET"])
def home():
    """Home page."""
    return jsonify({"Hello": "World!", "FLASK_ENV": FLASK_ENV})


@blueprint.route("/health", methods=["GET"])
def health():
    """Health."""
    return "OK"
