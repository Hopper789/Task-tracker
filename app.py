import os
import json
from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta, timezone
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)

# Конфигурация из переменных окружения
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://habit_user:sudo@localhost:5432/habit_tracker')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-123')

db = SQLAlchemy(app)

# Настройка логирования
if not os.path.exists('logs'):
    os.mkdir('logs')

file_handler = RotatingFileHandler('logs/habit_tracker.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Habit Tracker startup')

# Модели базы данных (остаются без изменений)
class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    logs = db.relationship('HabitLog', backref='habit', cascade="all, delete-orphan", lazy=True)
    activity_logs = db.relationship('ActivityLog', backref='habit', cascade="all, delete-orphan", lazy=True)

class HabitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    date = db.Column(db.Date, default=date.today, nullable=False, index=True)
    status = db.Column(db.Boolean, default=False)

    # Уникальный индекс для предотвращения дубликатов
    __table_args__ = (db.UniqueConstraint('habit_id', 'date', name='unique_habit_date'),)

class ActivityLog(db.Model):
    """Модель для логирования действий пользователя"""
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)  # create, update, delete, toggle, etc.
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)

# Вспомогательная функция для логирования
def log_activity(action, habit_id=None, details=None, request=None):
    """Логирует действие пользователя"""
    try:
        activity_log = ActivityLog(
            habit_id=habit_id,
            action=action,
            details=details,
            ip_address=request.remote_addr if request else None,
            user_agent=request.user_agent.string if request else None
        )
        db.session.add(activity_log)
        db.session.commit()
        
        # Также логируем в файл
        log_message = f"Action: {action}, Habit ID: {habit_id}, Details: {details}"
        app.logger.info(log_message)
        
    except Exception as e:
        app.logger.error(f"Failed to log activity: {e}")
        db.session.rollback()

def calculate_streak(habit_id):
    """Рассчитывает текущую серию непрерывного выполнения привычки"""
    today = date.today()
    
    # Получаем все выполненные записи, отсортированные по дате (от новых к старым)
    logs = HabitLog.query.filter_by(habit_id=habit_id, status=True)\
                         .order_by(HabitLog.date.desc())\
                         .all()
    
    if not logs:
        return 0
    
    # Определяем, есть ли сегодня выполнение
    has_today = logs[0].date == today
    
    # Определяем дату, с которой начинать подсчет
    if has_today:
        current_date = today
    else:
        # Если сегодня нет выполнения, проверяем вчера
        if logs[0].date == today - timedelta(days=1):
            current_date = today - timedelta(days=1)
        else:
            # Последнее выполнение было раньше чем вчера
            return 0
    
    # Подсчитываем непрерывные дни
    streak = 0
    for log in logs:
        if log.date == current_date:
            streak += 1
            current_date -= timedelta(days=1)
        else:
            break
    
    return streak

def get_weekly_stats(habit_id, weeks=8):
    """Получает статистику по неделям за последние N недель"""
    today = date.today()
    start_date = today - timedelta(weeks=weeks * 7)
    
    # Получаем все логи за период
    logs = HabitLog.query.filter(
        HabitLog.habit_id == habit_id,
        HabitLog.date >= start_date,
        HabitLog.status == True
    ).all()
    
    # Группируем по неделям
    weekly_data = {}
    for i in range(weeks):
        week_start = today - timedelta(weeks=weeks - i - 1)
        week_end = week_start + timedelta(days=6)
        week_key = week_start.strftime('%d.%m')
        
        # Подсчитываем выполненные дни за неделю
        count = sum(1 for log in logs if week_start <= log.date <= week_end)
        weekly_data[week_key] = min(count, 7)  # Максимум 7 дней в неделе
    
    return weekly_data

# Функция для форматирования дней в русском языке
def russian_plural_days(n):
    """Возвращает правильную форму слова 'день' для русского языка"""
    if n % 10 == 1 and n % 100 != 11:
        return "день"
    elif n % 10 in [2, 3, 4] and n % 100 not in [12, 13, 14]:
        return "дня"
    else:
        return "дней"

@app.route('/')
def index():
    today = date.today()
    habits_raw = Habit.query.all()
    habit_data = []
    
    # Генерируем 14 точек для истории (последние 2 недели)
    last_14_days = [(today - timedelta(days=i)) for i in range(13, -1, -1)]
    
    for h in habits_raw:
        log_today = HabitLog.query.filter_by(habit_id=h.id, date=today).first()
        
        # Рассчитываем текущую серию
        current_streak = calculate_streak(h.id)
        
        # Получаем историю за 14 дней
        two_week_history = []
        for d in last_14_days:
            l = HabitLog.query.filter_by(habit_id=h.id, date=d).first()
            two_week_history.append(l.status if l else False)
        
        # Рассчитываем прогресс за 2 недели
        completed_last_14 = sum(two_week_history)
        progress_percentage = int((completed_last_14 / 14) * 100) if two_week_history else 0
        
        habit_data.append({
            'id': h.id,
            'name': h.name,
            'done_today': log_today.status if log_today else False,
            'current_streak': current_streak,
            'two_week_history': two_week_history,
            'progress_percentage': progress_percentage,
            'completed_last_14': completed_last_14,
            'total_last_14': 14
        })
    
    # Рассчитываем общую статистику для отображения
    total_habits = len(habits_raw)
    completed_today = sum(1 for h in habit_data if h['done_today'])
    
    log_activity('view_index', details=f'Total habits: {total_habits}', request=request)
    
    # Передаем функции в шаблон
    return render_template('index.html', 
                         habits=habit_data, 
                         today=today,
                         timedelta=timedelta,
                         russian_plural_days=russian_plural_days,
                         total_habits=total_habits,
                         completed_today=completed_today)

@app.route('/add', methods=['POST'])
def add_habit():
    name = request.form.get('name')
    if name:
        new_habit = Habit(name=name.strip())
        db.session.add(new_habit)
        db.session.commit()
        
        # Логируем создание привычки
        log_activity('create_habit', habit_id=new_habit.id, 
                    details=f'Name: {name}', request=request)
        
        app.logger.info(f"Habit created: {name} (ID: {new_habit.id})")
    else:
        log_activity('create_habit_failed', details='Empty name provided', request=request)
        app.logger.warning("Attempt to create habit with empty name")
    
    return redirect(url_for('index'))

@app.route('/toggle/<int:habit_id>')
def toggle_today(habit_id):
    habit = db.session.get(Habit, habit_id)
    if not habit:
        log_activity('toggle_failed', habit_id=habit_id, 
                    details='Habit not found', request=request)
        abort(404)
    
    today = date.today()
    log = HabitLog.query.filter_by(habit_id=habit_id, date=today).first()
    
    old_status = log.status if log else False
    new_status = not old_status if log else True
    
    if log:
        log.status = new_status
    else:
        log = HabitLog(habit_id=habit_id, date=today, status=True)
        db.session.add(log)
    
    db.session.commit()
    
    # Логируем переключение
    log_activity('toggle_habit', habit_id=habit_id, 
                details=f'Date: {today}, Status: {old_status} -> {new_status}', 
                request=request)
    
    app.logger.info(f"Habit {habit_id} toggled: {old_status} -> {new_status}")
    
    return redirect(url_for('index'))

@app.route('/history/<int:habit_id>')
@app.route('/history/<int:habit_id>/<string:view>')
def history(habit_id, view='2weeks'):
    habit = db.session.get(Habit, habit_id)
    if not habit:
        abort(404)
    
    log_activity('view_history', habit_id=habit_id, 
                details=f'View: {view}', request=request)
    
    current_streak = calculate_streak(habit_id)
    
    if view == '2weeks':
        days_count = 14
        days = [date.today() - timedelta(days=i) for i in range(days_count - 1, -1, -1)]
        chart_title = "За последние 2 недели"
    else:
        weekly_data = get_weekly_stats(habit_id, 8)
        days = []
        chart_title = "Статистика по неделям (8 недель)"
    
    editable_days = [date.today() - timedelta(days=i) for i in range(13, -1, -1)]
    editable_history = []
    
    for d in editable_days:
        log = HabitLog.query.filter_by(habit_id=habit_id, date=d).first()
        is_done = log.status if log else False
        editable_history.append({
            'date': d, 
            'status': is_done,
            'date_str': d.strftime('%Y-%m-%d'),
            'day_name': d.strftime('%A')
        })
    
    if view == '2weeks':
        labels = [d.strftime('%d.%m') for d in days]
        values = []
        for d in days:
            log = HabitLog.query.filter_by(habit_id=habit_id, date=d).first()
            values.append(1 if log and log.status else 0)
    else:
        weekly_data = get_weekly_stats(habit_id, 8)
        labels = list(weekly_data.keys())
        values = list(weekly_data.values())
    
    completed_total = sum(1 for entry in editable_history if entry['status'])
    total_days = len(editable_history)
    percentage = int((completed_total / total_days * 100)) if total_days > 0 else 0
    
    return render_template('history.html', 
                           habit=habit,
                           labels=json.dumps(labels),
                           values=json.dumps(values),
                           history=editable_history,
                           current_streak=current_streak,
                           view=view,
                           chart_title=chart_title,
                           completed_total=completed_total,
                           total_days=total_days,
                           percentage=percentage,
                           russian_plural_days=russian_plural_days,
                           timedelta=timedelta)

@app.route('/history_update/<int:habit_id>/<string:log_date>', methods=['POST'])
def history_update(habit_id, log_date):
    try:
        target_date = datetime.strptime(log_date, '%Y-%m-%d').date()
        log = HabitLog.query.filter_by(habit_id=habit_id, date=target_date).first()
        
        old_status = log.status if log else False
        new_status = 'status' in request.form
        
        if log:
            log.status = new_status
        else:
            log = HabitLog(habit_id=habit_id, date=target_date, status=new_status)
            db.session.add(log)
        
        db.session.commit()
        
        # Логируем обновление истории
        log_activity('update_history', habit_id=habit_id, 
                    details=f'Date: {target_date}, Status: {old_status} -> {new_status}', 
                    request=request)
        
        app.logger.info(f"History updated: Habit {habit_id}, Date {target_date}: {old_status} -> {new_status}")
        
    except Exception as e:
        app.logger.error(f"Error updating history: {e}")
        log_activity('update_history_error', habit_id=habit_id, 
                    details=f'Error: {str(e)}', request=request)
    
    return redirect(request.referrer or url_for('index'))

@app.route('/delete/<int:habit_id>', methods=['POST'])
def delete_habit(habit_id):
    habit = db.session.get(Habit, habit_id)
    if not habit:
        log_activity('delete_failed', habit_id=habit_id, 
                    details='Habit not found', request=request)
        abort(404)
    
    habit_name = habit.name
    
    # Логируем перед удалением
    log_activity('delete_habit', habit_id=habit_id, 
                details=f'Name: {habit_name}', request=request)
    
    db.session.delete(habit)
    db.session.commit()
    
    app.logger.info(f"Habit deleted: {habit_name} (ID: {habit_id})")
    
    return redirect(url_for('index'))

@app.route('/api/weekly_stats/<int:habit_id>')
def api_weekly_stats(habit_id):
    """API для получения статистики по неделям"""
    weeks = request.args.get('weeks', 8, type=int)
    weekly_data = get_weekly_stats(habit_id, weeks)
    
    log_activity('api_call', habit_id=habit_id, 
                details=f'weekly_stats, weeks={weeks}', request=request)
    
    return jsonify(weekly_data)

@app.route('/logs')
def view_logs():
    """Страница для просмотра логов"""
    # Получаем последние 100 записей
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(100).all()
    
    # Форматируем для отображения
    formatted_logs = []
    for log in logs:
        formatted_logs.append({
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'habit_id': log.habit_id,
            'action': log.action,
            'details': log.details,
            'ip': log.ip_address
        })
    
    log_activity('view_logs', details=f'Viewed {len(logs)} logs', request=request)
    
    return render_template('logs.html', logs=formatted_logs)

@app.route('/logs/clear', methods=['POST'])
def clear_logs():
    """Очистка логов (только для админа)"""
    try:
        # Удаляем логи старше 30 дней
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        deleted_count = ActivityLog.query.filter(ActivityLog.timestamp < cutoff_date).delete()
        db.session.commit()
        
        log_activity('clear_logs', details=f'Deleted {deleted_count} old logs', request=request)
        app.logger.info(f"Cleared {deleted_count} old logs")
        
        return jsonify({'success': True, 'deleted': deleted_count})
    except Exception as e:
        app.logger.error(f"Error clearing logs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def init_db():
    """Инициализация базы данных"""
    with app.app_context():
        db.create_all()
        app.logger.info("Database tables created")

if __name__ == '__main__':
    init_db()
    app.logger.info(f"URL: http://localhost:5000")
    app.run(debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true', 
            host='0.0.0.0', 
            port=int(os.getenv('FLASK_PORT', 5000)))