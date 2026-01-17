minikube start --nodes 3 --memory=4096 --cpus=2

# Docker
docker build -t habit-tracker-app:latest .
minikube image load habit-tracker-app:latest

# Apply yaml
kubectl apply -f k8s/1-namespace.yaml
kubectl apply -f k8s/4-configmap.yaml
kubectl apply -f k8s/2-postgres.yaml
sleep 30
kubectl apply -f k8s/3-app.yaml
sleep 30

# Launch web
minikube service habit-tracker-external -n habit-tracker

echo ""
echo "🔧 Полезные команды:"
echo "   Просмотр логов: kubectl logs deployment/habit-tracker-app -n habit-tracker -f"
echo "   Подключиться к БД: kubectl exec -it deployment/postgres -n habit-tracker -- psql -U habit_user -d habit_tracker"
echo "   Удалить всё: kubectl delete namespace habit-tracker"