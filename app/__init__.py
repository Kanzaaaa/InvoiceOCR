import logging

from flask import Flask
from flask_cors import CORS

from app.celery_app import init_celery
from app.config import Config
from app.db import init_pool
from app.errors import register_error_handlers
from app.routes.exports import exports_bp
from app.routes.health import health_bp
from app.routes.ingestion import ingestion_bp
from app.routes.system import system_bp
from app.routes.tables import tables_bp


def create_app() -> Flask:
    app = Flask(__name__)
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)
    app.config.from_object(Config)
    app.config["POSTGRES_DSN"] = Config.database_url()
    CORS(
        app,
        resources={r"/api/*": {"origins": Config.CORS_ORIGINS}, r"/health": {"origins": Config.CORS_ORIGINS}},
    )

    Config.ensure_directories()
    init_pool(app)
    init_celery(app)

    app.register_blueprint(health_bp)
    app.register_blueprint(ingestion_bp, url_prefix="/api")
    app.register_blueprint(exports_bp, url_prefix="/api")
    app.register_blueprint(tables_bp, url_prefix="/api")
    app.register_blueprint(system_bp, url_prefix="/api")
    register_error_handlers(app)

    return app
