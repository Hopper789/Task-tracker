# conftest.py
import os
import sys
import pytest

# Устанавливаем переменные окружения для тестов
os.environ['FLASK_ENV'] = 'testing'

# Импортируем app ДО настройки
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Переопределяем конфигурацию
from app import db, app as flask_app

# Настраиваем для тестов
flask_app.config.update({
    'TESTING': True,
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'SECRET_KEY': 'test-secret-key',
    'WTF_CSRF_ENABLED': False
})

@pytest.fixture(autouse=True)
def setup_test_database():
    """Автоматически настраивает тестовую БД"""
    with flask_app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()

@pytest.fixture
def app():
    return flask_app

@pytest.fixture
def client(app):
    return app.test_client()