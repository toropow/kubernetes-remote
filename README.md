# Kubernetes Operations with Testcontainers

Этот проект предоставляет Python-модули для работы с Kubernetes кластером и Docker контейнерами через testcontainers. Особенностью реализации является то, что Kubernetes кластер находится вне testcontainers - это позволяет использовать любой существующий кластер, в то время как testcontainers используется для управления дополнительными тестовыми контейнерами.

## Архитектура

Проект состоит из двух основных компонентов:
1. **Kubernetes Operations** - работает с внешним Kubernetes кластером через официальный kubernetes-client
2. **Container Operations** - управляет локальными Docker контейнерами через testcontainers

Такая архитектура позволяет:
- Использовать существующий Kubernetes кластер для основных операций
- Запускать дополнительные тестовые контейнеры локально через testcontainers
- Обеспечивать взаимодействие между локальными контейнерами и кластером
- Тестировать различные сценарии развертывания и интеграции

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

# Создание port-forward
k8s.port_forward(
    pod_name="my-pod",
    local_port=8888,
    pod_port=80
)

# Остановка конкретного port-forward
k8s.stop_port_forward("my-pod", 8888)

# Создание NodePort service
k8s.expose_service_nodeport(
    service_name="my-service",
    port=80,
    target_port=8080,
    node_port=30001
)

# Удаление ресурсов и очистка port-forward
k8s.cleanup()  # Останавливает все port-forward
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
            
            # Создание port-forward к поду
            k8s.port_forward(
                pod_name="example-pod",
                local_port=8888,
                pod_port=80
            )

            # Создание NodePort service
            k8s.expose_service_nodeport(
                service_name="example-service",
                port=80,
                target_port=8080,
                node_port=30001
            )

            print("Приложение доступно:")
            print("- Через port-forward: http://localhost:8888")
            print("- Через NodePort: http://localhost:30001")

    finally:
        # Очистка ресурсов
        k8s.cleanup()  # Останавливает все port-forward
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

## Особенности работы с Testcontainers

При работе с testcontainers важно помнить:
1. Testcontainers используется только для управления локальными Docker контейнерами
2. Kubernetes кластер должен быть настроен отдельно и доступен через `~/.kube/config`
3. Локальные контейнеры могут взаимодействовать с сервисами в кластере через:
   - NodePort
   - Port-forward
   - Ingress (если настроен)

### Примеры интеграции

```python
# Запуск тестового контейнера через testcontainers
container = containers.start_container(
    name="test-app",
    image="nginx:latest",
    ports={80: 8080}
)

# Взаимодействие с Kubernetes кластером
k8s.create_deployment("deployment.yaml")
k8s.create_service("service.yaml")

# Создание port-forward для доступа к поду из локального контейнера
k8s.port_forward(
    pod_name="example-pod",
    local_port=8888,
    pod_port=80
)
```

## Обработка ошибок

Все методы в модулях включают обработку ошибок и возвращают:
- Успешный результат операции или
- `None`/`False` в случае ошибки

При возникновении ошибок в консоль выводится информативное сообщение об ошибке.

## Безопасность

- Убедитесь, что файл `~/.kube/config` имеет правильные права доступа
- Не храните чувствительные данные в коде или конфигурационных файлах
- Используйте переменные окружения для хранения секретов
- При использовании port-forward учитывайте, что порты будут доступны локально

## Лицензия

MIT 