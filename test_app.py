import pytest
from app import app, db, Habit

@pytest.fixture
def client():
    app.config['TESTING'] = True
    # ЗАГЛУШКА: Для тестов лучше использовать sqlite в памяти или тестовую БД Postgres
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client

def test_index_page(client):
    rv = client.get('/')
    assert rv.status_code == 200

def test_add_habit(client):
    client.post('/add', data={'name': 'Сделать зарядку'})
    habit = Habit.query.first()
    assert habit.name == 'Сделать зарядку'
