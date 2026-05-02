import os
import tempfile

import pytest

from app import app as flask_app
from database.db import init_db


@pytest.fixture()
def app():
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    flask_app.config.update(TESTING=True, DATABASE=db_path, SECRET_KEY='test-secret')
    with flask_app.app_context():
        init_db()
    yield flask_app
    os.close(db_fd)
    try:
        os.unlink(db_path)
    except PermissionError:
        pass  # Windows may hold the WAL file briefly; OS cleanup handles it


@pytest.fixture()
def client(app):
    return app.test_client()
