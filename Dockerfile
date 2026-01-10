# FROM python:3.12-alpine AS server
# WORKDIR /app

# # Установка библиотек
# COPY requirements.txt .
# RUN pip install -r requirements.txt && \
#     rm requirements.txt && \
#     mkdir templates && \
#     mkdir logs

# # Добавление исходников
# COPY templates/* ./templates/ \
#     app.py ./ \
#     confest.py ./

# ENTRYPOINT ["python3", "app.py"]

# # БАЗА ДАННЫХ!

# # docker volume create habit-tracker-logs
# # docker build -t habit-tracker .

# # docker run -p 5000:5000 \
# #     -v habit-tracker-logs:/app/logs \
# #     habit-tracker 


FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt update && apt install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements и установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание пользователя для безопасности
RUN useradd -m -u 1000 habituser && chown -R habituser:habituser /app
USER habituser

EXPOSE 5000

CMD ["python", "app.py"]