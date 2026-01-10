#!/bin/bash

echo "Waiting for PostgreSQL to start..."
while ! pg_isready -h postgres -p 5432 -U habit_user; do
    sleep 1
done

echo "PostgreSQL started successfully"

# Инициализация базы данных
echo "Initializing database..."
python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database initialized')
"

# Запуск приложения
echo "Starting Flask application..."
exec python app.py