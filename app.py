import os
import json
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta

app = Flask(__name__)

# Используйте правильную строку подключения
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://habit_user:sudo@localhost:5432/habit_tracker'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev-secret-key-123'  # Добавьте секретный ключ

db = SQLAlchemy(app)

# Модели базы данных
class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    logs = db.relationship('HabitLog', backref='habit', cascade="all, delete-orphan", lazy=True)

class HabitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    date = db.Column(db.Date, default=date.today, nullable=False)
    status = db.Column(db.Boolean, default=False)

@app.route('/')
def index():
    today = date.today()
    habits_raw = Habit.query.all()
    habit_data = []
    
    # Генерируем 5 точек для мини-истории (последние 5 дней)
    last_5_days = [(today - timedelta(days=i)) for i in range(4, -1, -1)]
    
    for h in habits_raw:
        log_today = HabitLog.query.filter_by(habit_id=h.id, date=today).first()
        
        mini_history = []
        for d in last_5_days:
            l = HabitLog.query.filter_by(habit_id=h.id, date=d).first()
            mini_history.append(l.status if l else False)
            
        habit_data.append({
            'id': h.id,
            'name': h.name,
            'done_today': log_today.status if log_today else False,
            'mini_history': mini_history
        })
    
    return render_template('index.html', habits=habit_data)

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
def history(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    
    # Последние 7 дней для графика
    days = [date.today() - timedelta(days=i) for i in range(6, -1, -1)]
    
    labels_list = [d.strftime('%d.%m') for d in days]
    values_list = []
    editable_history = []
    
    for d in days:
        log = HabitLog.query.filter_by(habit_id=habit_id, date=d).first()
        is_done = log.status if log else False
        values_list.append(1 if is_done else 0)
        editable_history.append({
            'date': d, 
            'status': is_done,
            'date_str': d.strftime('%Y-%m-%d')  # Добавляем строковое представление для формы
        })
    
    # Сортируем историю по дате (от новых к старым)
    editable_history.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('history.html', 
                           habit=habit, 
                           labels=json.dumps(labels_list), 
                           values=json.dumps(values_list),
                           history=editable_history)

@app.route('/history_update/<int:habit_id>/<string:log_date>', methods=['POST'])
def history_update(habit_id, log_date):
    try:
        target_date = datetime.strptime(log_date, '%Y-%m-%d').date()
        log = HabitLog.query.filter_by(habit_id=habit_id, date=target_date).first()
        
        # Проверяем, есть ли статус в форме (чекбокс отправляется только если отмечен)
        status = 'status' in request.form
        
        if log:
            log.status = status
        else:
            db.session.add(HabitLog(habit_id=habit_id, date=target_date, status=status))
        
        db.session.commit()
    except Exception as e:
        print(f"Error updating history: {e}")
    
    return redirect(url_for('history', habit_id=habit_id))

@app.route('/delete/<int:habit_id>', methods=['POST'])
def delete_habit(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    db.session.delete(habit)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        # Создаем все таблицы
        db.create_all()
        print("База данных инициализирована")
        print(f"URL: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)