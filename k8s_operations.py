from kubernetes import client, config
from kubernetes.stream import stream
from kubernetes.stream import portforward
import yaml
import os
import socket
import threading
import time

class KubernetesOperations:
    def __init__(self):
        # Загружаем конфигурацию из файла ~/.kube/config
        config.load_kube_config()
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.port_forward_processes = {}

    def create_deployment(self, yaml_file):
        """
        Создает deployment из yaml файла
        """
        with open(yaml_file) as f:
            dep = yaml.safe_load(f)
            try:
                resp = self.apps_v1.create_namespaced_deployment(
                    body=dep,
                    namespace="default"
                )
                print(f"Deployment {resp.metadata.name} создан")
                return resp
            except Exception as e:
                print(f"Ошибка при создании deployment: {e}")
                return None

    def create_service(self, yaml_file):
        """
        Создает service из yaml файла
        """
        with open(yaml_file) as f:
            svc = yaml.safe_load(f)
            try:
                resp = self.v1.create_namespaced_service(
                    body=svc,
                    namespace="default"
                )
                print(f"Service {resp.metadata.name} создан")
                return resp
            except Exception as e:
                print(f"Ошибка при создании service: {e}")
                return None

    def delete_deployment(self, name, namespace="default"):
        """
        Удаляет deployment по имени
        """
        try:
            resp = self.apps_v1.delete_namespaced_deployment(
                name=name,
                namespace=namespace,
                body=client.V1DeleteOptions(
                    propagation_policy="Foreground",
                    grace_period_seconds=5
                )
            )
            print(f"Deployment {name} удален")
            return resp
        except Exception as e:
            print(f"Ошибка при удалении deployment: {e}")
            return None

    def delete_service(self, name, namespace="default"):
        """
        Удаляет service по имени
        """
        try:
            resp = self.v1.delete_namespaced_service(
                name=name,
                namespace=namespace
            )
            print(f"Service {name} удален")
            return resp
        except Exception as e:
            print(f"Ошибка при удалении service: {e}")
            return None

    def exec_command_in_pod(self, pod_name, namespace="default", command=None):
        """
        Выполняет команду внутри pod
        """
        if command is None:
            command = ['/bin/sh']
            
        try:
            resp = stream(self.v1.connect_get_namespaced_pod_exec,
                        pod_name,
                        namespace,
                        command=command,
                        stderr=True,
                        stdin=False,
                        stdout=True,
                        tty=False)
            return resp
        except Exception as e:
            print(f"Ошибка при выполнении команды в pod: {e}")
            return None

    def expose_service_nodeport(self, service_name, namespace="default", port=80, target_port=80, node_port=30000):
        """
        Создает NodePort service для доступа к приложению извне кластера
        """
        try:
            service_manifest = {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {
                    "name": service_name
                },
                "spec": {
                    "type": "NodePort",
                    "ports": [{
                        "port": port,
                        "targetPort": target_port,
                        "nodePort": node_port
                    }],
                    "selector": {
                        "app": service_name
                    }
                }
            }
            
            resp = self.v1.create_namespaced_service(
                namespace=namespace,
                body=service_manifest
            )
            print(f"NodePort Service {service_name} создан на порту {node_port}")
            return resp
        except Exception as e:
            print(f"Ошибка при создании NodePort service: {e}")
            return None

    def port_forward(self, pod_name: str, local_port: int, pod_port: int, namespace: str = "default") -> bool:
        """
        Создает port-forward из пода на локальный порт

        Args:
            pod_name: Имя пода
            local_port: Локальный порт
            pod_port: Порт в поде
            namespace: Namespace пода

        Returns:
            bool: True если port-forward успешно создан, False в случае ошибки
        """
        try:
            # Проверяем, не занят ли уже порт
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if sock.connect_ex(('127.0.0.1', local_port)) == 0:
                print(f"Порт {local_port} уже используется")
                return False
            sock.close()

            # Создаем port-forward
            pf = portforward(self.v1.connect_get_namespaced_pod_portforward,
                           pod_name,
                           namespace,
                           ports=str(pod_port))

            # Запускаем port-forward в отдельном потоке
            def _port_forward():
                try:
                    pf.socket(pod_port).connect(('localhost', local_port))
                    pf.run()
                except Exception as e:
                    print(f"Ошибка в port-forward для пода {pod_name}: {e}")

            thread = threading.Thread(target=_port_forward, daemon=True)
            thread.start()

            # Сохраняем процесс для возможности остановки
            self.port_forward_processes[(pod_name, local_port)] = (pf, thread)

            # Ждем немного, чтобы убедиться, что port-forward запустился
            time.sleep(2)
            
            # Проверяем, что порт теперь доступен
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if sock.connect_ex(('127.0.0.1', local_port)) == 0:
                print(f"Port-forward создан: localhost:{local_port} -> pod {pod_name}:{pod_port}")
                sock.close()
                return True
            else:
                print(f"Не удалось установить port-forward для пода {pod_name}")
                self.stop_port_forward(pod_name, local_port)
                return False

        except Exception as e:
            print(f"Ошибка при создании port-forward для пода {pod_name}: {e}")
            return False

    def stop_port_forward(self, pod_name: str, local_port: int) -> bool:
        """
        Останавливает port-forward

        Args:
            pod_name: Имя пода
            local_port: Локальный порт

        Returns:
            bool: True если port-forward успешно остановлен, False в случае ошибки
        """
        try:
            key = (pod_name, local_port)
            if key in self.port_forward_processes:
                pf, thread = self.port_forward_processes[key]
                pf.close()
                del self.port_forward_processes[key]
                print(f"Port-forward остановлен для пода {pod_name} на порту {local_port}")
                return True
            else:
                print(f"Port-forward не найден для пода {pod_name} на порту {local_port}")
                return False
        except Exception as e:
            print(f"Ошибка при остановке port-forward: {e}")
            return False

    def cleanup(self):
        """
        Очищает все активные port-forward соединения
        """
        for pod_name, local_port in list(self.port_forward_processes.keys()):
            self.stop_port_forward(pod_name, local_port) 