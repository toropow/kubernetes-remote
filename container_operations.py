from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
import docker
from typing import Optional, Dict, List
import time

class ContainerOperations:
    def __init__(self):
        self.client = docker.from_env()
        self.containers = {}

    def start_container(
        self,
        name: str,
        image: str,
        environment: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[int, int]] = None,
        command: Optional[str] = None,
        network_mode: str = "bridge"
    ) -> DockerContainer:
        """
        Запускает контейнер с заданными параметрами
        
        Args:
            name: Имя контейнера
            image: Docker image
            environment: Переменные окружения
            ports: Маппинг портов {container_port: host_port}
            command: Команда для запуска
            network_mode: Режим сети (bridge, host, etc.)
        """
        try:
            container = DockerContainer(image)
            
            if name:
                container.with_name(name)
            
            if environment:
                for key, value in environment.items():
                    container.with_env(key, value)
            
            if ports:
                for container_port, host_port in ports.items():
                    container.with_bind_ports(container_port, host_port)

            if command:
                container.with_command(command)

            container.with_kwargs(network_mode=network_mode)
            
            container.start()
            self.containers[name] = container
            
            print(f"Контейнер {name} успешно запущен")
            return container
            
        except Exception as e:
            print(f"Ошибка при запуске контейнера {name}: {e}")
            return None

    def stop_container(self, name: str) -> bool:
        """
        Останавливает контейнер по имени
        """
        try:
            if name in self.containers:
                container = self.containers[name]
                container.stop()
                del self.containers[name]
                print(f"Контейнер {name} остановлен")
                return True
            else:
                print(f"Контейнер {name} не найден")
                return False
        except Exception as e:
            print(f"Ошибка при остановке контейнера {name}: {e}")
            return False

    def wait_for_container_log(self, name: str, message: str, timeout: int = 30) -> bool:
        """
        Ожидает появления определенного сообщения в логах контейнера
        """
        try:
            if name in self.containers:
                container = self.containers[name]
                wait_for_logs(container, message, timeout)
                return True
            return False
        except Exception as e:
            print(f"Ошибка при ожидании лога в контейнере {name}: {e}")
            return False

    def get_container_logs(self, name: str) -> Optional[str]:
        """
        Получает логи контейнера
        """
        try:
            if name in self.containers:
                container = self.containers[name]
                return container.get_logs()
            return None
        except Exception as e:
            print(f"Ошибка при получении логов контейнера {name}: {e}")
            return None

    def cleanup(self):
        """
        Останавливает все запущенные контейнеры
        """
        for name in list(self.containers.keys()):
            self.stop_container(name) 