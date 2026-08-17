from secrets import compare_digest

from flask import Blueprint, current_app, jsonify, request, session
from werkzeug.exceptions import Unauthorized

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username") or "")
    password = str(payload.get("password") or "")

    expected_username = str(current_app.config["APP_USERNAME"])
    expected_password = str(current_app.config["APP_PASSWORD"])
    if not compare_digest(username, expected_username) or not compare_digest(password, expected_password):
        raise Unauthorized("Invalid username or password")

    session.clear()
    session["authenticated"] = True
    session["username"] = username
    return jsonify({"authenticated": True, "username": username})


@auth_bp.post("/auth/logout")
def logout():
    session.clear()
    return jsonify({"authenticated": False})


@auth_bp.get("/auth/me")
def current_user():
    authenticated = bool(session.get("authenticated"))
    return jsonify(
        {
            "authenticated": authenticated,
            "username": session.get("username") if authenticated else None,
        }
    )
