from flask import jsonify
from werkzeug.exceptions import HTTPException


def register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify({"error": error.description, "status_code": error.code}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        return jsonify({"error": str(error), "status_code": 500}), 500
