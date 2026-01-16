#!/bin/bash

echo "🚀 1. Запускаем Minikube..."
minikube start --driver=docker

echo "📦 2. Собираем Docker образ..."
docker build -t habit-tracker-app:latest .
minikube image load habit-tracker-app:latest

echo "🛠 3. Применяем конфигурацию Kubernetes..."
kubectl apply -f k8s/1-namespace.yaml
kubectl apply -f k8s/2-postgres.yaml

echo "⏳ Ждем запуска PostgreSQL..."
sleep 30

kubectl apply -f k8s/3-app.yaml

echo "⏳ Ждем запуска приложения..."
sleep 20

echo "✅ Всё запущено!"
echo ""
echo "📊 Проверь статус:"
kubectl get all -n habit-tracker

echo ""
echo "🌐 Открой приложение в браузере:"
minikube service habit-tracker-external -n habit-tracker

echo ""
echo "🔧 Полезные команды:"
echo "   Просмотр логов: kubectl logs deployment/habit-tracker-app -n habit-tracker -f"
echo "   Подключиться к БД: kubectl exec -it deployment/postgres -n habit-tracker -- psql -U habit_user -d habit_tracker"
echo "   Удалить всё: kubectl delete namespace habit-tracker"