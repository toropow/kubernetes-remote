from kubernetes import client, config
from kubernetes.stream import stream
import yaml
import time
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("k8s_operations")


class KubernetesOperations:
    def __init__(self, context=None):
        # Загружаем конфигурацию из файла ~/.kube/config
        try:
            if context:
                config.load_kube_config(context=context)
            else:
                config.load_kube_config()
            self.v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            logger.info("Kubernetes клиент инициализирован успешно")
        except Exception as e:
            logger.error(f"Ошибка при инициализации Kubernetes клиента: {e}")
            raise

    def resource_exists(self, name: str, namespace: str = "default", resource_type: str = "deployment") -> bool:
        """
        Проверяет существование ресурса в кластере

        Args:
            name: Имя ресурса
            namespace: Namespace ресурса
            resource_type: Тип ресурса ('deployment', 'service', 'pod', etc.)

        Returns:
            bool: True если ресурс существует, False если нет
        """
        try:
            if resource_type == "deployment":
                self.apps_v1.read_namespaced_deployment(name, namespace)
            elif resource_type == "service":
                self.v1.read_namespaced_service(name, namespace)
            elif resource_type == "pod":
                self.v1.read_namespaced_pod(name, namespace)
            else:
                logger.warning(f"Неизвестный тип ресурса: {resource_type}")
                return False
            return True
        except client.exceptions.ApiException as e:
            if e.status == 404:
                return False
            logger.error(f"API ошибка при проверке ресурса {resource_type}/{name}: {e}")
            raise e
        except Exception as e:
            logger.error(f"Ошибка при проверке ресурса {resource_type}/{name}: {e}")
            return False

    def create_deployment(self, yaml_file, wait_ready=False, timeout=60):
        """
        Создает deployment из yaml файла

        Args:
            yaml_file: Путь к YAML файлу
            wait_ready: Ожидать ли готовности подов
            timeout: Таймаут ожидания в секундах

        Returns:
            Объект Deployment или None в случае ошибки
        """
        try:
            with open(yaml_file) as f:
                dep = yaml.safe_load(f)

            name = dep["metadata"]["name"]
            namespace = dep["metadata"].get("namespace", "default")

            # Проверяем существование deployment
            if self.resource_exists(name, namespace, "deployment"):
                logger.info(f"Deployment {name} уже существует, обновляем...")
                resp = self.apps_v1.replace_namespaced_deployment(name=name, namespace=namespace, body=dep)
            else:
                logger.info(f"Создаем новый deployment {name}...")
                resp = self.apps_v1.create_namespaced_deployment(body=dep, namespace=namespace)

            logger.info(f"Deployment {resp.metadata.name} создан/обновлен")

            # Ожидаем готовности подов, если нужно
            if wait_ready and "spec" in dep and "selector" in dep["spec"] and "matchLabels" in dep["spec"]["selector"]:
                labels = dep["spec"]["selector"]["matchLabels"]
                label_selector = ",".join([f"{k}={v}" for k, v in labels.items()])
                if self.wait_for_pod_ready(label_selector, namespace, timeout):
                    logger.info(f"Поды deployment {name} готовы")
                else:
                    logger.warning(f"Таймаут ожидания готовности подов deployment {name}")

            return resp
        except Exception as e:
            logger.error(f"Ошибка при создании deployment из файла {yaml_file}: {e}")
            return None

    def create_service(self, yaml_file):
        """
        Создает service из yaml файла
        """
        try:
            with open(yaml_file) as f:
                svc = yaml.safe_load(f)

            name = svc["metadata"]["name"]
            namespace = svc["metadata"].get("namespace", "default")

            # Проверяем существование service
            if self.resource_exists(name, namespace, "service"):
                logger.info(f"Service {name} уже существует, обновляем...")
                resp = self.v1.replace_namespaced_service(name=name, namespace=namespace, body=svc)
            else:
                logger.info(f"Создаем новый service {name}...")
                resp = self.v1.create_namespaced_service(body=svc, namespace=namespace)

            logger.info(f"Service {resp.metadata.name} создан/обновлен")
            return resp
        except Exception as e:
            logger.error(f"Ошибка при создании service из файла {yaml_file}: {e}")
            return None

    def delete_deployment(self, name, namespace="default"):
        """
        Удаляет deployment по имени
        """
        try:
            if not self.resource_exists(name, namespace, "deployment"):
                logger.info(f"Deployment {name} не существует, пропускаем удаление")
                return True

            resp = self.apps_v1.delete_namespaced_deployment(
                name=name,
                namespace=namespace,
                body=client.V1DeleteOptions(propagation_policy="Foreground", grace_period_seconds=5),
            )
            logger.info(f"Deployment {name} удален")
            return resp
        except Exception as e:
            logger.error(f"Ошибка при удалении deployment {name}: {e}")
            return None

    def delete_service(self, name, namespace="default"):
        """
        Удаляет service по имени
        """
        try:
            if not self.resource_exists(name, namespace, "service"):
                logger.info(f"Service {name} не существует, пропускаем удаление")
                return True

            resp = self.v1.delete_namespaced_service(name=name, namespace=namespace)
            logger.info(f"Service {name} удален")
            return resp
        except Exception as e:
            logger.error(f"Ошибка при удалении service {name}: {e}")
            return None

    def exec_command_in_pod(self, pod_name, namespace="default", command=None, timeout=30):
        """
        Выполняет команду внутри pod

        Args:
            pod_name: Имя пода
            namespace: Namespace пода
            command: Команда для выполнения в виде списка
            timeout: Таймаут выполнения команды в секундах

        Returns:
            str: Результат выполнения команды или None в случае ошибки
        """
        if command is None:
            command = ["/bin/sh"]

        try:
            if not self.resource_exists(pod_name, namespace, "pod"):
                logger.error(f"Под {pod_name} не существует")
                return None

            logger.info(f"Выполняем команду {command} в поде {pod_name}")
            resp = stream(
                self.v1.connect_get_namespaced_pod_exec,
                pod_name,
                namespace,
                command=command,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False,
                _request_timeout=timeout,
            )
            return resp
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды в pod {pod_name}: {e}")
            return None

    def expose_service_nodeport(
        self, service_name, selector=None, namespace="default", port=80, target_port=80, node_port=30000
    ):
        """
        Создает NodePort service для доступа к приложению извне кластера

        Args:
            service_name: Имя сервиса
            selector: Селектор для выбора подов (dict)
            namespace: Namespace сервиса
            port: Порт сервиса
            target_port: Целевой порт в поде
            node_port: Порт на ноде

        Returns:
            Объект Service или None в случае ошибки
        """
        try:
            # Если сервис уже существует, удаляем его
            if self.resource_exists(service_name, namespace, "service"):
                logger.info(f"Service {service_name} уже существует, удаляем...")
                self.delete_service(service_name, namespace)

            # Если селектор не указан, используем имя сервиса как метку app
            if selector is None:
                selector = {"app": service_name}

            service_manifest = {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {"name": service_name},
                "spec": {
                    "type": "NodePort",
                    "ports": [{"port": port, "targetPort": target_port, "nodePort": node_port}],
                    "selector": selector,
                },
            }

            logger.info(f"Создаем NodePort service {service_name} на порту {node_port}")
            resp = self.v1.create_namespaced_service(namespace=namespace, body=service_manifest)
            logger.info(f"NodePort Service {service_name} создан на порту {node_port}")
            return resp
        except Exception as e:
            logger.error(f"Ошибка при создании NodePort service {service_name}: {e}")
            return None

    def get_pod_name_by_label(self, label_selector: str, namespace: str = "default") -> str:
        """
        Получает имя пода по метке

        Args:
            label_selector: Селектор меток (например, "app=kafka-ui")
            namespace: Namespace пода

        Returns:
            str: Имя пода или None, если под не найден
        """
        try:
            logger.info(f"Поиск пода по метке {label_selector} в namespace {namespace}")
            pods = self.v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector)

            if pods.items:
                # Берем первый запущенный под
                for pod in pods.items:
                    if pod.status.phase == "Running":
                        logger.info(f"Найден запущенный под {pod.metadata.name}")
                        return pod.metadata.name

                # Если нет запущенных, берем первый под
                logger.warning(
                    f"Запущенные поды не найдены, используем первый доступный: {pods.items[0].metadata.name}"
                )
                return pods.items[0].metadata.name

            logger.warning(f"Под с меткой {label_selector} не найден")
            return None
        except Exception as e:
            logger.error(f"Ошибка при поиске пода по метке {label_selector}: {e}")
            return None

    def wait_for_pod_ready(self, label_selector: str, namespace: str = "default", timeout: int = 60) -> bool:
        """
        Ожидает готовности пода

        Args:
            label_selector: Селектор меток (например, "app=kafka-ui")
            namespace: Namespace пода
            timeout: Таймаут в секундах

        Returns:
            bool: True если под готов, False в случае ошибки или таймаута
        """
        try:
            logger.info(f"Ожидание готовности пода с меткой {label_selector}, таймаут {timeout} сек")
            start_time = time.time()
            while time.time() - start_time < timeout:
                pods = self.v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector)

                if not pods.items:
                    logger.warning(f"Поды с меткой {label_selector} не найдены, ожидаем...")
                    time.sleep(2)
                    continue

                # Проверяем статус подов
                ready_pods = 0
                total_pods = len(pods.items)

                for pod in pods.items:
                    if pod.status.phase == "Running":
                        # Проверяем, что все контейнеры готовы
                        if pod.status.container_statuses and all(
                            container.ready for container in pod.status.container_statuses
                        ):
                            ready_pods += 1

                logger.info(f"Готово {ready_pods}/{total_pods} подов")

                if ready_pods == total_pods and total_pods > 0:
                    logger.info(f"Все поды готовы ({total_pods})")
                    return True

                time.sleep(2)

            logger.warning(f"Таймаут ожидания готовности пода ({timeout} сек)")
            return False
        except Exception as e:
            logger.error(f"Ошибка при ожидании готовности пода: {e}")
            return False

    def wait_for_kafka_ready(self, pod_name=None, label_selector=None, namespace="default", timeout=120):
        """
        Ожидает готовности Kafka в поде Kubernetes

        Args:
            pod_name: Имя пода с Kafka (если не указано, будет использован label_selector)
            label_selector: Селектор меток для поиска пода (например, "app=kafka")
            namespace: Namespace пода
            timeout: Таймаут ожидания в секундах

        Returns:
            bool: True если Kafka готова, False в случае ошибки или таймаута
        """
        try:
            # Получаем имя пода, если указан label_selector
            if pod_name is None and label_selector is not None:
                logger.info(f"Поиск пода Kafka по метке {label_selector}")
                pod_name = self.get_pod_name_by_label(label_selector, namespace)
                if pod_name is None:
                    logger.error(f"Не удалось найти под Kafka по метке {label_selector}")
                    return False
            elif pod_name is None:
                logger.error("Необходимо указать pod_name или label_selector")
                return False

            logger.info(f"Ожидание готовности Kafka в поде {pod_name}, таймаут {timeout} сек")

            # Ожидаем готовности пода
            if not self.resource_exists(pod_name, namespace, "pod"):
                logger.error(f"Под {pod_name} не существует")
                return False

            # Проверяем статус Kafka с помощью команд
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Проверка через kafka-topics
                result = self.exec_command_in_pod(
                    pod_name=pod_name,
                    namespace=namespace,
                    command=[
                        "/bin/sh",
                        "-c",
                        "kafka-topics.sh --list --bootstrap-server localhost:9092 2>/dev/null || kafka-topics --list --bootstrap-server localhost:9092 2>/dev/null",
                    ],
                    timeout=10,
                )

                if result is not None and not "Error" in result:
                    logger.info(f"Kafka в поде {pod_name} готова (по проверке команды)")
                    return True

                # Альтернативная проверка через kafka-broker-api-versions
                result = self.exec_command_in_pod(
                    pod_name=pod_name,
                    namespace=namespace,
                    command=[
                        "/bin/sh",
                        "-c",
                        "kafka-broker-api-versions.sh --bootstrap-server localhost:9092 2>/dev/null || kafka-broker-api-versions --bootstrap-server localhost:9092 2>/dev/null",
                    ],
                    timeout=10,
                )

                if result is not None and "Supported" in result:
                    logger.info(f"Kafka в поде {pod_name} готова (по проверке API версий)")
                    return True

                # Проверка через grep логов (если доступен)
                result = self.exec_command_in_pod(
                    pod_name=pod_name,
                    namespace=namespace,
                    command=[
                        "/bin/sh",
                        "-c",
                        "grep 'started (kafka.server.KafkaServer)' /var/log/kafka/server.log 2>/dev/null || grep 'started (kafka.server.KafkaServer)' /logs/server.log 2>/dev/null",
                    ],
                    timeout=10,
                )

                if result is not None and "started" in result:
                    logger.info(f"Kafka в поде {pod_name} готова (по логам)")
                    return True

                # Ждем перед следующей попыткой
                time.sleep(5)
                logger.info(
                    f"Ожидание Kafka в поде {pod_name}... прошло {int(time.time() - start_time)} сек из {timeout}"
                )

            logger.warning(f"Таймаут ожидания готовности Kafka в поде {pod_name} ({timeout} сек)")
            return False
        except Exception as e:
            logger.error(f"Ошибка при ожидании готовности Kafka в поде {pod_name}: {e}")
            return False

    def cleanup(self):
        """
        Очищает ресурсы
        """
        logger.info("Очистка ресурсов Kubernetes завершена")
        # Место для дополнительной логики очистки ресурсов, если потребуется
