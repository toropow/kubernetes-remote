from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
import docker
from typing import Optional, Dict, List
import time
import logging

# Настраиваем логирование, используя тот же формат
logger = logging.getLogger("container_operations")


class ContainerOperations:
    def __init__(self):
        try:
            self.client = docker.from_env()
            self.containers = {}
            logger.info("Docker клиент инициализирован успешно")
        except Exception as e:
            logger.error(f"Ошибка при инициализации Docker клиента: {e}")
            raise

    def start_container(
        self,
        name: str,
        image: str,
        environment: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[int, int]] = None,
        command: Optional[str] = None,
        network_mode: str = "bridge",
        volumes: Optional[Dict[str, str]] = None,
        pull_image: bool = False,
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
            volumes: Маппинг томов {host_path: container_path}
            pull_image: Нужно ли подтягивать образ перед запуском
        """
        try:
            logger.info(f"Запуск контейнера {name} (образ: {image})")

            # Проверяем, не запущен ли уже контейнер с таким именем
            if name in self.containers:
                logger.warning(f"Контейнер с именем {name} уже запущен, останавливаем его")
                self.stop_container(name)

            # Подтягиваем образ, если нужно
            if pull_image:
                logger.info(f"Подтягиваем образ {image}")
                try:
                    self.client.images.pull(image)
                except Exception as e:
                    logger.warning(f"Не удалось подтянуть образ {image}: {e}")

            container = DockerContainer(image)

            if name:
                container.with_name(name)
                logger.debug(f"Установлено имя контейнера: {name}")

            if environment:
                for key, value in environment.items():
                    container.with_env(key, value)
                logger.debug(f"Установлены переменные окружения: {environment}")

            if ports:
                for container_port, host_port in ports.items():
                    container.with_bind_ports(container_port, host_port)
                logger.debug(f"Установлены порты: {ports}")

            if command:
                container.with_command(command)
                logger.debug(f"Установлена команда: {command}")

            if volumes:
                for host_path, container_path in volumes.items():
                    container.with_volume_mapping(host_path, container_path)
                logger.debug(f"Установлены тома: {volumes}")

            container.with_kwargs(network_mode=network_mode)
            logger.debug(f"Установлен режим сети: {network_mode}")

            container.start()
            self.containers[name] = container

            logger.info(f"Контейнер {name} успешно запущен")
            return container

        except Exception as e:
            logger.error(f"Ошибка при запуске контейнера {name}: {e}")
            return None

    def stop_container(self, name: str) -> bool:
        """
        Останавливает контейнер по имени
        """
        try:
            if name in self.containers:
                logger.info(f"Останавливаем контейнер {name}")
                container = self.containers[name]
                container.stop()
                del self.containers[name]
                logger.info(f"Контейнер {name} остановлен")
                return True
            else:
                logger.warning(f"Контейнер {name} не найден")
                return False
        except Exception as e:
            logger.error(f"Ошибка при остановке контейнера {name}: {e}")
            return False

    def wait_for_container_log(self, name: str, message: str, timeout: int = 30) -> bool:
        """
        Ожидает появления определенного сообщения в логах контейнера
        """
        try:
            if name in self.containers:
                logger.info(
                    f"Ожидание появления сообщения '{message}' в логах контейнера {name}, таймаут {timeout} сек"
                )
                container = self.containers[name]
                wait_for_logs(container, message, timeout)
                logger.info(f"Сообщение '{message}' найдено в логах контейнера {name}")
                return True
            logger.warning(f"Контейнер {name} не найден для ожидания лога")
            return False
        except Exception as e:
            logger.error(f"Ошибка при ожидании лога в контейнере {name}: {e}")
            return False

    def get_container_logs(self, name: str, tail: int = 100) -> Optional[str]:
        """
        Получает логи контейнера

        Args:
            name: Имя контейнера
            tail: Количество последних строк для возврата

        Returns:
            str: Логи контейнера или None в случае ошибки
        """
        try:
            if name in self.containers:
                logger.debug(f"Получение логов контейнера {name}")
                container = self.containers[name]
                logs = container.get_logs()

                # Если нужно ограничить количество строк
                if tail > 0 and logs:
                    logs_lines = logs.strip().split("\n")
                    if len(logs_lines) > tail:
                        logs = "\n".join(logs_lines[-tail:])

                return logs
            logger.warning(f"Контейнер {name} не найден для получения логов")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении логов контейнера {name}: {e}")
            return None

    def get_container_status(self, name: str) -> Optional[str]:
        """
        Получает статус контейнера

        Args:
            name: Имя контейнера

        Returns:
            str: Статус контейнера или None в случае ошибки
        """
        try:
            if name in self.containers:
                container = self.containers[name]
                # Обновляем информацию о контейнере
                docker_container = self.client.containers.get(container.get_wrapped_container().id)
                status = docker_container.status
                logger.debug(f"Статус контейнера {name}: {status}")
                return status
            logger.warning(f"Контейнер {name} не найден для получения статуса")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении статуса контейнера {name}: {e}")
            return None

    def exec_in_container(self, name: str, command: List[str]) -> Optional[str]:
        """
        Выполняет команду в контейнере

        Args:
            name: Имя контейнера
            command: Команда для выполнения в виде списка

        Returns:
            str: Результат выполнения команды или None в случае ошибки
        """
        try:
            if name in self.containers:
                logger.info(f"Выполнение команды {command} в контейнере {name}")
                container = self.containers[name]
                docker_container = self.client.containers.get(container.get_wrapped_container().id)
                result = docker_container.exec_run(command)
                output = result.output.decode("utf-8")
                return output
            logger.warning(f"Контейнер {name} не найден для выполнения команды")
            return None
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды в контейнере {name}: {e}")
            return None

    def wait_for_kafka_ready(self, container_name: str, timeout: int = 120) -> bool:
        """
        Ожидает готовности Kafka в контейнере

        Args:
            container_name: Имя контейнера с Kafka
            timeout: Таймаут ожидания в секундах

        Returns:
            bool: True если Kafka готова, False в случае ошибки или таймаута
        """
        try:
            logger.info(f"Ожидание готовности Kafka в контейнере {container_name}, таймаут {timeout} сек")

            # Проверяем существование контейнера
            if container_name not in self.containers:
                logger.error(f"Контейнер {container_name} не найден")
                return False

            # Способ 1: Ожидание характерного сообщения в логах
            kafka_ready_message = "started (kafka.server.KafkaServer)"
            if self.wait_for_container_log(container_name, kafka_ready_message, timeout):
                logger.info(f"Kafka в контейнере {container_name} готова (по логам)")
                return True

            # Способ 2: Проверка с помощью kafka-topics или kafka-broker-api-versions
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Проверка работоспособности с помощью команды kafka-topics
                result = self.exec_in_container(
                    container_name,
                    [
                        "/bin/sh",
                        "-c",
                        "kafka-topics.sh --list --bootstrap-server localhost:9092 2>/dev/null || kafka-topics --list --bootstrap-server localhost:9092 2>/dev/null",
                    ],
                )

                if result is not None and not "Error" in result:
                    logger.info(f"Kafka в контейнере {container_name} готова (по проверке команды)")
                    return True

                # Альтернативная проверка с помощью kafka-broker-api-versions
                result = self.exec_in_container(
                    container_name,
                    [
                        "/bin/sh",
                        "-c",
                        "kafka-broker-api-versions.sh --bootstrap-server localhost:9092 2>/dev/null || kafka-broker-api-versions --bootstrap-server localhost:9092 2>/dev/null",
                    ],
                )

                if result is not None and "Supported" in result:
                    logger.info(f"Kafka в контейнере {container_name} готова (по проверке API версий)")
                    return True

                # Ждем перед следующей попыткой
                time.sleep(5)

            logger.warning(f"Таймаут ожидания готовности Kafka в контейнере {container_name} ({timeout} сек)")
            return False
        except Exception as e:
            logger.error(f"Ошибка при ожидании готовности Kafka в контейнере {container_name}: {e}")
            return False

    def cleanup(self):
        """
        Останавливает все запущенные контейнеры
        """
        logger.info(f"Очистка всех контейнеров ({len(self.containers)} шт.)")
        for name in list(self.containers.keys()):
            self.stop_container(name)
