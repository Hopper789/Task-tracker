# test_config.py
import sys
import os

# Устанавливаем переменные окружения ДО импорта app
os.environ['CI'] = 'true'
os.environ['TESTING'] = 'true'

# Патчим app.py перед импортом
with open('app.py', 'r') as f:
    content = f.read()

# Заменяем строку подключения на SQLite
new_content = content.replace(
    "app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://habit_user:sudo@localhost:5432/habit_tracker'",
    """
    # Автоматически используем SQLite для тестов
    import os
    if os.environ.get('CI') or os.environ.get('TESTING'):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://habit_user:sudo@localhost:5432/habit_tracker'
    """
)

# Записываем во временный файл
temp_app_path = 'app_patched_for_tests.py'
with open(temp_app_path, 'w') as f:
    f.write(new_content)

# Теперь импортируем из патченного файла
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Экспортируем все что нужно
from app_patched_for_tests import app, db, Habit, HabitLog, ActivityLog, calculate_streak, get_weekly_stats, russian_plural_days, log_activity

# Удаляем временный файл после импорта
import atexit
@atexit.register
def cleanup():
    if os.path.exists(temp_app_path):
        os.remove(temp_app_path)

__all__ = ['app', 'db', 'Habit', 'HabitLog', 'ActivityLog', 'calculate_streak', 'get_weekly_stats', 'russian_plural_days', 'log_activity']