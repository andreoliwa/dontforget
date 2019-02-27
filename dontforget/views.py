"""Public section, including homepage and signup."""
from flask import Blueprint, jsonify
from prettyconf import config

blueprint = Blueprint("public", __name__, static_folder="../static")


@blueprint.route("/", methods=["GET"])
def home():
    """Redirect to user."""
    return jsonify({"Hello": "World!", "FLASK_ENV": config("FLASK_ENV")})


@blueprint.route("/health", methods=["GET"])
def health():
    """Health."""
    return "OK"
