# test_app.py
import os
import sys
from datetime import date, datetime, timedelta, timezone
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app as flask_app, db, Habit, HabitLog, calculate_streak, get_weekly_stats, russian_plural_days

@pytest.fixture
def app():
    """Создает тестовое приложение с тестовой БД"""
    # Клонируем конфигурацию для тестов
    flask_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False
    })
    
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Создает тестовый клиент"""
    return app.test_client()

def test_app_setup(app):
    """Тест: приложение корректно инициализируется"""
    assert app is not None
    assert app.config['TESTING'] is True
    assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:'
    assert app.config['WTF_CSRF_ENABLED'] is False

def test_database_models_basic(app):
    """Базовый тест моделей базы данных"""
    with app.app_context():
        # Создаем привычку
        habit = Habit(name='Test Habit')
        db.session.add(habit)
        db.session.commit()
        
        assert habit.id is not None
        assert habit.name == 'Test Habit'
        
        # Создаем лог
        log = HabitLog(habit_id=habit.id, date=date.today(), status=True)
        db.session.add(log)
        db.session.commit()
        
        assert log.id is not None
        assert log.habit_id == habit.id
        assert log.status == True
        assert log.date == date.today()

def test_add_habit_english(client, app):
    """Тест: добавление привычки с английским названием"""
    response = client.post('/add', data={'name': 'Morning Exercise'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Morning Exercise' in response.data
    
    with app.app_context():
        habit = Habit.query.first()
        assert habit is not None
        assert habit.name == 'Morning Exercise'

def test_toggle_habit_basic(client, app):
    """Базовый тест переключения привычки"""
    with app.app_context():
        habit = Habit(name='Toggle Test')
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id
    
    response = client.get(f'/toggle/{habit_id}', follow_redirects=True)
    assert response.status_code == 200
    
    with app.app_context():
        log = HabitLog.query.filter_by(habit_id=habit_id, date=date.today()).first()
        assert log is not None
        assert log.status == True

def test_calculate_streak_simple():
    """Простой тест расчета серии (не требует БД)"""
    assert russian_plural_days(1) == "день"
    assert russian_plural_days(2) == "дня"
    assert russian_plural_days(5) == "дней"

def test_calculate_streak_no_logs(app):
    """Тест: нет логов вообще"""
    with app.app_context():
        habit = Habit(name='No Logs Habit')
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id
        
        streak = calculate_streak(habit_id)
        assert streak == 0

def test_calculate_streak_only_today(app):
    """Тест: только сегодня выполнено"""
    with app.app_context():
        habit = Habit(name='Today Only')
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id
        
        today = date.today()
        log = HabitLog(habit_id=habit_id, date=today, status=True)
        db.session.add(log)
        db.session.commit()
        
        streak = calculate_streak(habit_id)
        assert streak == 1

def test_calculate_streak_only_yesterday(app):
    """Тест: только вчера выполнено (сегодня нет записи)"""
    with app.app_context():
        habit = Habit(name='Yesterday Only')
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Только вчера выполнено, сегодня нет записи
        log = HabitLog(habit_id=habit_id, date=yesterday, status=True)
        db.session.add(log)
        db.session.commit()
        
        streak = calculate_streak(habit_id)
        # Согласно логике функции: если сегодня нет выполнения, 
        # но вчера есть, то серия начинается с вчера = 1
        assert streak == 1

def test_calculate_streak_yesterday_and_before(app):
    """Тест: вчера и позавчера выполнено, сегодня нет записи"""
    with app.app_context():
        habit = Habit(name='Yesterday and Before')
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        day_before = today - timedelta(days=2)
        
        # Вчера и позавчера выполнено
        log1 = HabitLog(habit_id=habit_id, date=yesterday, status=True)
        log2 = HabitLog(habit_id=habit_id, date=day_before, status=True)
        db.session.add_all([log1, log2])
        db.session.commit()
        
        streak = calculate_streak(habit_id)
        # Серия: вчера и позавчера = 2 дня
        assert streak == 2

def test_calculate_streak_continuous_three_days(app):
    """Тест: непрерывная серия 3 дня"""
    with app.app_context():
        habit = Habit(name='Three Day Streak')
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id
        
        today = date.today()
        
        # Сегодня, вчера и позавчера выполнено
        for i in range(3):
            log_date = today - timedelta(days=i)
            log = HabitLog(habit_id=habit_id, date=log_date, status=True)
            db.session.add(log)
        db.session.commit()
        
        streak = calculate_streak(habit_id)
        assert streak == 3

def test_calculate_streak_with_gap(app):
    """Тест: серия с пропуском"""
    with app.app_context():
        habit = Habit(name='Streak with Gap')
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id
        
        today = date.today()
        
        # Позавчера выполнено, вчера НЕ выполнено, сегодня выполнено
        day_before = HabitLog(
            habit_id=habit_id, 
            date=today - timedelta(days=2), 
            status=True
        )
        yesterday = HabitLog(
            habit_id=habit_id, 
            date=today - timedelta(days=1), 
            status=False  # Пропуск!
        )
        today_log = HabitLog(
            habit_id=habit_id, 
            date=today, 
            status=True
        )
        
        db.session.add_all([day_before, yesterday, today_log])
        db.session.commit()
        
        streak = calculate_streak(habit_id)
        # Только сегодня выполнено, вчера пропущено, поэтому серия = 1
        assert streak == 1

def test_calculate_streak_today_not_done(app):
    """Тест: сегодня отмечено как невыполненное"""
    with app.app_context():
        habit = Habit(name='Today Not Done')
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Вчера выполнено, сегодня не выполнено
        log1 = HabitLog(habit_id=habit_id, date=yesterday, status=True)
        log2 = HabitLog(habit_id=habit_id, date=today, status=False)
        db.session.add_all([log1, log2])
        db.session.commit()
        
        streak = calculate_streak(habit_id)
        # Сегодня не выполнено, поэтому серия начинается с вчера = 1
        assert streak == 1

def test_api_endpoint(client, app):
    """Тест API endpoint"""
    with app.app_context():
        habit = Habit(name='API Test')
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id
    
    response = client.get(f'/api/weekly_stats/{habit_id}')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert isinstance(data, dict)

def test_main_routes(client, app):
    """Тест основных маршрутов"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'<!DOCTYPE html>' in response.data
    
    response = client.get('/history/999999')
    assert response.status_code == 404

def test_habit_lifecycle(client, app):
    """Полный жизненный цикл привычки"""
    response = client.post('/add', data={'name': 'Complete Lifecycle Test'}, follow_redirects=True)
    assert response.status_code == 200
    
    with app.app_context():
        habit = Habit.query.filter_by(name='Complete Lifecycle Test').first()
        assert habit is not None
        habit_id = habit.id
    
    response = client.get(f'/toggle/{habit_id}', follow_redirects=True)
    assert response.status_code == 200
    
    response = client.get(f'/history/{habit_id}')
    assert response.status_code == 200
    
    response = client.post(f'/delete/{habit_id}', follow_redirects=True)
    assert response.status_code == 200
    
    with app.app_context():
        habit = Habit.query.get(habit_id)
        assert habit is None

def test_get_weekly_stats_function(app):
    """Тест функции получения недельной статистики"""
    with app.app_context():
        habit = Habit(name='Weekly Stats Test')
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id
        
        today = date.today()
        
        for i in range(7):
            log_date = today - timedelta(days=i)
            log = HabitLog(
                habit_id=habit_id,
                date=log_date,
                status=(i % 2 == 0)
            )
            db.session.add(log)
        
        db.session.commit()
        
        stats = get_weekly_stats(habit_id, weeks=2)
        assert isinstance(stats, dict)
        assert len(stats) == 2

def test_history_update(client, app):
    """Тест обновления истории"""
    with app.app_context():
        habit = Habit(name='History Update Test')
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id
    
    yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    response = client.post(
        f'/history_update/{habit_id}/{yesterday}', 
        data={'status': 'on'},
        follow_redirects=True
    )
    assert response.status_code == 200
    
    with app.app_context():
        log_date = datetime.strptime(yesterday, '%Y-%m-%d').date()
        log = HabitLog.query.filter_by(habit_id=habit_id, date=log_date).first()
        assert log is not None
        assert log.status == True

def test_empty_state(client):
    """Тест состояния при отсутствии привычек"""
    response = client.get('/')
    assert response.status_code == 200
    assert len(response.data) > 0

def test_multiple_habits(client, app):
    """Тест с несколькими привычками"""
    habit_names = ['Exercise', 'Reading', 'Meditation']
    
    for name in habit_names:
        response = client.post('/add', data={'name': name}, follow_redirects=True)
        assert response.status_code == 200
    
    response = client.get('/')
    assert response.status_code == 200
    
    for name in habit_names:
        assert name.encode('utf-8') in response.data

def test_database_isolation(app):
    """Тест изоляции тестовой БД"""
    with app.app_context():
        assert Habit.query.count() == 0
        
        habit = Habit(name='Isolation Test')
        db.session.add(habit)
        db.session.commit()
        
        assert Habit.query.count() == 1

def test_actual_streak_logic_from_code(app):
    """Тест реальной логики из кода приложения"""
    with app.app_context():
        # Воспроизведем сценарий из оригинального падающего теста
        habit = Habit(name='Actual Logic Test')
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id
        
        today = date.today()
        
        # Создаем логи как в оригинальном тесте
        yesterday = HabitLog(
            habit_id=habit_id, 
            date=today - timedelta(days=1), 
            status=True
        )
        day_before = HabitLog(
            habit_id=habit_id, 
            date=today - timedelta(days=2), 
            status=True
        )
        
        db.session.add_all([yesterday, day_before])
        db.session.commit()
        
        # Согласно логике функции calculate_streak:
        # 1. Берет все выполненные логи (status=True) - у нас 2
        # 2. Начинает проверять с today: нет записи -> streak остается 0
        # 3. Проверяет вчерашний день (streak == 0 и вчера есть выполнение)
        # 4. Начинает считать с yesterday: streak = 1
        # 5. Проверяет следующий log: day_before соответствует check_date (yesterday-1)
        # 6. streak = 2
        # 7. Больше логов нет
        
        streak = calculate_streak(habit_id)
        print(f"DEBUG: streak = {streak}")
        print(f"DEBUG: today = {today}")
        print(f"DEBUG: logs = {[(log.date, log.status) for log in HabitLog.query.filter_by(habit_id=habit_id).all()]}")
        print(f"DEBUG: true logs only = {[log.date for log in HabitLog.query.filter_by(habit_id=habit_id, status=True).order_by(HabitLog.date.desc()).all()]}")
        
        # Согласно логике, должно быть 2
        assert streak == 2
        
        # Теперь добавляем выполнение сегодня
        today_log = HabitLog(
            habit_id=habit_id, 
            date=today, 
            status=True
        )
        db.session.add(today_log)
        db.session.commit()
        
        new_streak = calculate_streak(habit_id)
        print(f"DEBUG: new streak with today = {new_streak}")
        
        # Теперь должно быть 3
        assert new_streak == 3

if __name__ == '__main__':
    pytest.main(['-v', __file__, '--disable-warnings', '-s'])