FROM python:3.11-slim
WORKDIR /app

# Установка зависимостей
RUN apt update && apt install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

ENTRYPOINT ["python", "app.py"]