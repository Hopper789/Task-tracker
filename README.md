## Это приложение для трекинга привычек
просто приложене для трекинга привычек и ничего более
## Запуск тестов
```
python -m pytest test_app.py -v
```
## Сборка и запуск образов
```
docker compose up --build
```

## Проверка бд
```
psql -U habit_user -d habit_tracker -h localhost -p 228
```

## Хочу вставить одну команду
```
git clone https://github.com/Hopper789/Task-tracker.git 
cd Task-tracker
docker compose up --build
```