import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

app = Flask(__name__)

# Настройки БД
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://habit_user:password@localhost/habit_tracker'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Модель привычки
class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    logs = db.relationship('HabitLog', backref='habit', cascade="all, delete-orphan", lazy=True)

# Модель лога (выполнено или нет на конкретную дату)
class HabitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    date = db.Column(db.Date, default=date.today)
    status = db.Column(db.Boolean, default=False)

@app.route('/')
def index():
    today = date.today()
    habits = Habit.query.all()
    # Собираем данные: выполнена ли привычка сегодня
    habit_data = []
    for h in habits:
        log = HabitLog.query.filter_by(habit_id=h.id, date=today).first()
        habit_data.append({
            'id': h.id,
            'name': h.name,
            'done_today': log.status if log else False
        })
    return render_template('index.html', habits=habit_data, today=today)

@app.route('/add', methods=['POST'])
def add_habit():
    name = request.form.get('name')
    if name:
        new_habit = Habit(name=name)
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
        new_log = HabitLog(habit_id=habit_id, date=today, status=True)
        db.session.add(new_log)
    db.session.commit()
    return redirect(url_for('index'))

# Новое: редактирование истории (за последние 7 дней)
@app.route('/history/<int:habit_id>')
def history(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    import datetime as dt
    days = [date.today() - dt.timedelta(days=i) for i in range(7)]
    history_data = []
    for d in days:
        log = HabitLog.query.filter_by(habit_id=habit_id, date=d).first()
        history_data.append({'date': d, 'status': log.status if log else False})
    return render_template('history.html', habit=habit, history=history_data)

@app.route('/history_update/<int:habit_id>/<string:log_date>', methods=['POST'])
def history_update(habit_id, log_date):
    target_date = datetime.strptime(log_date, '%Y-%m-%d').date()
    log = HabitLog.query.filter_by(habit_id=habit_id, date=target_date).first()
    status = True if request.form.get('status') == 'on' else False
    
    if log:
        log.status = status
    else:
        new_log = HabitLog(habit_id=habit_id, date=target_date, status=status)
        db.session.add(new_log)
    db.session.commit()
    return redirect(url_for('history', habit_id=habit_id))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
