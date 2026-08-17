from app import create_app
from app.celery_app import celery

flask_app = create_app()

import app.tasks  # noqa: E402,F401
