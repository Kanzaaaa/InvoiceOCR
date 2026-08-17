from flask import jsonify, request, session


AUTH_EXEMPT_PATHS = {
    "/api/auth/login",
    "/api/auth/logout",
    "/api/auth/me",
    "/health",
}


def register_auth_guard(app):
    @app.before_request
    def require_authenticated_session():
        if request.method == "OPTIONS":
            return None
        if request.path in AUTH_EXEMPT_PATHS:
            return None
        if not request.path.startswith("/api/"):
            return None
        if session.get("authenticated"):
            return None
        return jsonify({"error": "Unauthorized", "status_code": 401}), 401
