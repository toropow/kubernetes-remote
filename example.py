from k8s_operations import KubernetesOperations
from container_operations import ContainerOperations
import time

def main():
    # Создаем экземпляры классов для работы с Kubernetes и контейнерами
    k8s = KubernetesOperations()
    containers = ContainerOperations()

    try:
        # Запускаем тестовый контейнер
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
            print("Ожидаем запуска контейнера...")
            time.sleep(5)  # Даем контейнеру время на запуск

            # Создаем deployment в Kubernetes
            k8s.create_deployment("deployment.yaml")
            
            # Создаем service в Kubernetes
            k8s.create_service("service.yaml")

            # Пример выполнения команды в поде
            pod_name = "example-pod"
            command = ["ls", "-la"]
            result = k8s.exec_command_in_pod(pod_name, command=command)
            print(f"Результат выполнения команды в поде: {result}")

            # Создаем port-forward к поду используя метку
            k8s.port_forward(
                pod_name="example-pod",  # Это значение игнорируется при использовании label_selector
                local_port=8888,
                pod_port=80,
                label_selector="app=example-app"  # Используем метку из deployment.yaml
            )

            # Альтернативный способ создания port-forward:
            # Сначала получаем имя пода по метке
            pod_name = k8s.get_pod_name_by_label("app=example-app")
            if pod_name:
                k8s.port_forward(
                    pod_name=pod_name,
                    local_port=8889,
                    pod_port=80
                )

            # Создаем NodePort service для доступа к приложению извне кластера
            k8s.expose_service_nodeport(
                service_name="example-service",
                port=80,
                target_port=8080,
                node_port=30001
            )

            print("Приложение доступно:")
            print("- Через port-forward (по метке): http://localhost:8888")
            print("- Через port-forward (по имени пода): http://localhost:8889")
            print("- Через NodePort: http://localhost:30001")
            print("Нажмите Ctrl+C для завершения...")
            
            while True:
                time.sleep(1)

    except KeyboardInterrupt:
        print("\nЗавершение работы...")
    finally:
        # Очистка ресурсов
        print("Очистка ресурсов...")
        k8s.cleanup()  # Остановка всех port-forward
        k8s.delete_service("example-service")
        k8s.delete_deployment("example-deployment")
        containers.cleanup()

if __name__ == "__main__":
    main() 