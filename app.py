import os
import json
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
from collections import defaultdict
from sqlalchemy import func

app = Flask(__name__)

# Используйте правильную строку подключения
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://habit_user:sudo@localhost:5432/habit_tracker'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev-secret-key-123'

db = SQLAlchemy(app)

# Модели базы данных
class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    logs = db.relationship('HabitLog', backref='habit', cascade="all, delete-orphan", lazy=True)

class HabitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    date = db.Column(db.Date, default=date.today, nullable=False, index=True)
    status = db.Column(db.Boolean, default=False)

    # Уникальный индекс для предотвращения дубликатов
    __table_args__ = (db.UniqueConstraint('habit_id', 'date', name='unique_habit_date'),)

def calculate_streak(habit_id):
    """Рассчитывает текущую серию непрерывного выполнения привычки"""
    today = date.today()
    streak = 0
    
    # Получаем все записи, отсортированные по дате (от новых к старым)
    logs = HabitLog.query.filter_by(habit_id=habit_id, status=True)\
                         .order_by(HabitLog.date.desc())\
                         .all()
    
    # Проверяем последовательные дни
    check_date = today
    for log in logs:
        if log.date == check_date:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break
    
    # Проверяем вчерашний день (если сегодня еще не отмечен)
    if streak == 0:
        yesterday = today - timedelta(days=1)
        yesterday_log = HabitLog.query.filter_by(habit_id=habit_id, date=yesterday, status=True).first()
        if yesterday_log:
            # Начинаем считать с вчерашнего дня
            check_date = yesterday
            streak = 1
            for log in logs:
                if log.date == check_date:
                    streak += 1
                    check_date -= timedelta(days=1)
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
    
    # Передаем функции в шаблон
    return render_template('index.html', 
                         habits=habit_data, 
                         today=today,
                         timedelta=timedelta,  # Добавляем timedelta в контекст
                         russian_plural_days=russian_plural_days,  # Функция для склонения
                         total_habits=total_habits,
                         completed_today=completed_today)

@app.route('/add', methods=['POST'])
def add_habit():
    name = request.form.get('name')
    if name:
        new_habit = Habit(name=name.strip())
        db.session.add(new_habit)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/toggle/<int:habit_id>')
def toggle_today(habit_id):
    today = date.today()
    log = HabitLog.query.filter_by(habit_id=habit_id, date=today).first()
    if log:
        log.status = not log.status
    else:
        db.session.add(HabitLog(habit_id=habit_id, date=today, status=True))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/history/<int:habit_id>')
@app.route('/history/<int:habit_id>/<string:view>')
def history(habit_id, view='2weeks'):
    habit = Habit.query.get_or_404(habit_id)
    
    current_streak = calculate_streak(habit_id)
    
    if view == '2weeks':
        # История за 2 недели (14 дней)
        days_count = 14
        days = [date.today() - timedelta(days=i) for i in range(days_count - 1, -1, -1)]
        chart_title = "За последние 2 недели"
    else:  # 8weeks
        # Статистика по неделям за 8 недель
        weekly_data = get_weekly_stats(habit_id, 8)
        days = []
        chart_title = "Статистика по неделям (8 недель)"
    
    # Данные для редактируемой истории (всегда за 14 дней)
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
    
    # Данные для графика
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
    
    # Подсчитываем статистику для отображения
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
        
        status = 'status' in request.form
        
        if log:
            log.status = status
        else:
            db.session.add(HabitLog(habit_id=habit_id, date=target_date, status=status))
        
        db.session.commit()
    except Exception as e:
        print(f"Error updating history: {e}")
    
    return redirect(request.referrer or url_for('index'))

@app.route('/delete/<int:habit_id>', methods=['POST'])
def delete_habit(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    db.session.delete(habit)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/api/weekly_stats/<int:habit_id>')
def api_weekly_stats(habit_id):
    """API для получения статистики по неделям"""
    weeks = request.args.get('weeks', 8, type=int)
    weekly_data = get_weekly_stats(habit_id, weeks)
    return jsonify(weekly_data)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("База данных инициализирована")
        print(f"URL: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)