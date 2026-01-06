# conftest.py
import os
import sys
import pytest

# Устанавливаем переменные окружения для тестов
os.environ['CI'] = 'true'
os.environ['TESTING'] = 'true'

# Патчим app.py перед импортом
with open('app.py', 'r') as f:
    content = f.read()

# Заменяем строку подключения на SQLite
if 'postgresql://' in content:
    content = content.replace(
        "app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://habit_user:sudo@localhost:5432/habit_tracker'",
        "app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'"
    )
    
    # Записываем обратно
    with open('app.py', 'w') as f:
        f.write(new_content)

# Теперь импортируем
from app import app as flask_app, db, Habit, HabitLog, ActivityLog, calculate_streak, get_weekly_stats, russian_plural_days, log_activity

@pytest.fixture(autouse=True)
def setup_test_database():
    """Автоматически настраивает тестовую БД"""
    # Дополнительная настройка для тестов
    flask_app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key'
    })
    
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