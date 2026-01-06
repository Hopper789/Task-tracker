# conftest.py
import pytest
from app import app, db

@pytest.fixture(autouse=True)
def setup_test_database():
    """Настройка тестовой базы данных перед каждым тестом"""
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()