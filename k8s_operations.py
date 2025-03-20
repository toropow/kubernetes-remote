from kubernetes import client, config
from kubernetes.stream import stream
import yaml
import os

class KubernetesOperations:
    def __init__(self):
        # Загружаем конфигурацию из файла ~/.kube/config
        config.load_kube_config()
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()

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