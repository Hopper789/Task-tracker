minikube addons enable ingress
minikube addons enable metrics-server


kubectl get pods -n habit-tracker -
kubectl logs deployment/habit-tracker-app -n habit-tracker --tail=10

minikube start --nodes 3 --memory=4096 --cpus=2
minikube image load habit-tracker-app:latest

# Остановить всё
kubectl delete namespace habit-tracker

# Остановить Minikube
minikube stop

# Полностью удалить
minikube delete


# Показать всё в namespace
kubectl get all -n habit-tracker
# Показать логи приложения
kubectl logs deployment/habit-tracker-app -n habit-tracker
# Перезапустить приложение
kubectl rollout restart deployment/habit-tracker-app -n habit-tracker
# Открыть в браузере
minikube service habit-tracker-external -n habit-tracker
# Удалить всё
kubectl delete namespace habit-tracker