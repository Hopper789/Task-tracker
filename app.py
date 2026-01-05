from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://habit_user:sudo@localhost/habit_tracker'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    logs = db.relationship('HabitLog', backref='habit', cascade="all, delete-orphan", lazy=True)

class HabitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    date = db.Column(db.Date, default=date.today)
    status = db.Column(db.Boolean, default=False)

@app.route('/')
def index():
    today = date.today()
    habits_raw = Habit.query.all()
    habit_data = []
    
    # Генерируем краткую историю (последние 5 дней) для главной страницы
    last_5_days = [(today - timedelta(days=i)) for i in range(4, -1, -1)]
    
    for h in habits_raw:
        log_today = HabitLog.query.filter_by(habit_id=h.id, date=today).first()
        
        # Собираем статусы за последние 5 дней для мини-точек
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
    return render_template('index.html', habits=habit_data, last_5_days=last_5_days)

@app.route('/add', methods=['POST'])
def add_habit():
    name = request.form.get('name')
    if name:
        db.session.add(Habit(name=name))
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/toggle/<int:habit_id>')
def toggle_today(habit_id):
    today = date.today()
    log = HabitLog.query.filter_by(habit_id=habit_id, date=today).first()
    if log: log.status = not log.status
    else: db.session.add(HabitLog(habit_id=habit_id, date=today, status=True))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/history/<int:habit_id>')
def history(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    # История за 7 дней для гистограммы
    days = [date.today() - timedelta(days=i) for i in range(6, -1, -1)]
    labels = [d.strftime('%a') for d in days]
    values = []
    editable_history = []
    
    for d in days:
        log = HabitLog.query.filter_by(habit_id=habit_id, date=d).first()
        is_done = log.status if log else False
        values.append(1 if is_done else 0)
        editable_history.append({'date': d, 'status': is_done})
        
    return render_template('history.html', 
                           habit=habit, 
                           labels=json.dumps(labels), 
                           values=json.dumps(values),
                           history=reversed(editable_history))

@app.route('/history_update/<int:habit_id>/<string:log_date>', methods=['POST'])
def history_update(habit_id, log_date):
    target_date = datetime.strptime(log_date, '%Y-%m-%d').date()
    log = HabitLog.query.filter_by(habit_id=habit_id, date=target_date).first()
    status = True if request.form.get('status') else False
    if log: log.status = status
    else: db.session.add(HabitLog(habit_id=habit_id, date=target_date, status=status))
    db.session.commit()
    return redirect(url_for('history', habit_id=habit_id))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
