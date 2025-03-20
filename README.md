# Kubernetes Operations with Testcontainers

Этот проект предоставляет Python-модули для работы с Kubernetes кластером и Docker контейнерами. Модули позволяют управлять deployment'ами, service'ами и контейнерами, а также выполнять команды внутри подов.

## Требования

- Python 3.7+
- Docker
- Доступ к Kubernetes кластеру
- Файл конфигурации Kubernetes (`~/.kube/config`)

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd kuber_project
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

## Структура проекта

- `k8s_operations.py` - модуль для работы с Kubernetes
- `container_operations.py` - модуль для работы с Docker контейнерами
- `example.py` - пример использования модулей
- `requirements.txt` - зависимости проекта

## Использование

### 1. Работа с Kubernetes

```python
from k8s_operations import KubernetesOperations

# Инициализация
k8s = KubernetesOperations()

# Создание deployment
k8s.create_deployment("deployment.yaml")

# Создание service
k8s.create_service("service.yaml")

# Выполнение команды в поде
result = k8s.exec_command_in_pod("pod-name", command=["ls", "-la"])

# Создание NodePort service
k8s.expose_service_nodeport(
    service_name="my-service",
    port=80,
    target_port=8080,
    node_port=30001
)

# Удаление ресурсов
k8s.delete_service("my-service")
k8s.delete_deployment("my-deployment")
```

### 2. Работа с Docker контейнерами

```python
from container_operations import ContainerOperations

# Инициализация
containers = ContainerOperations()

# Запуск контейнера
container = containers.start_container(
    name="my-container",
    image="nginx:latest",
    ports={80: 8080},
    environment={
        "ENV": "test",
        "APP_PORT": "80"
    }
)

# Получение логов
logs = containers.get_container_logs("my-container")

# Ожидание определенного сообщения в логах
containers.wait_for_container_log("my-container", "message to wait for")

# Остановка контейнера
containers.stop_container("my-container")

# Очистка всех контейнеров
containers.cleanup()
```

### 3. Полный пример использования

```python
from k8s_operations import KubernetesOperations
from container_operations import ContainerOperations
import time

def main():
    k8s = KubernetesOperations()
    containers = ContainerOperations()

    try:
        # Запуск тестового контейнера
        container = containers.start_container(
            name="test-app",
            image="nginx:latest",
            ports={80: 8080},
            environment={
                "ENV": "test",
                "APP_PORT": "80"
            }
        )

        if container:
            # Создание ресурсов в Kubernetes
            k8s.create_deployment("deployment.yaml")
            k8s.create_service("service.yaml")
            
            # Создание NodePort service
            k8s.expose_service_nodeport(
                service_name="example-service",
                port=80,
                target_port=8080,
                node_port=30001
            )

            # Получение логов
            logs = containers.get_container_logs("test-app")
            print("Логи контейнера:", logs)

    finally:
        # Очистка ресурсов
        k8s.delete_service("example-service")
        k8s.delete_deployment("example-deployment")
        containers.cleanup()

if __name__ == "__main__":
    main()
```

## Примеры YAML файлов

### deployment.yaml
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: example-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: example-app
  template:
    metadata:
      labels:
        app: example-app
    spec:
      containers:
      - name: example-container
        image: nginx:latest
        ports:
        - containerPort: 80
```

### service.yaml
```yaml
apiVersion: v1
kind: Service
metadata:
  name: example-service
spec:
  selector:
    app: example-app
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

## Обработка ошибок

Все методы в модулях включают обработку ошибок и возвращают:
- Успешный результат операции или
- `None` в случае ошибки

При возникновении ошибок в консоль выводится информативное сообщение об ошибке.

## Безопасность

- Убедитесь, что файл `~/.kube/config` имеет правильные права доступа
- Не храните чувствительные данные в коде или конфигурационных файлах
- Используйте переменные окружения для хранения секретов

## Лицензия

MIT 