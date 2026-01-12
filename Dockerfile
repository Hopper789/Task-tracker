FROM python:3.11-slim as builder
WORKDIR /app

# Установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

ENTRYPOINT ["python", "app.py"]