from k8s_operations import KubernetesOperations
from container_operations import ContainerOperations
import time


def main():
    # Создаем экземпляры классов для работы с Kubernetes и контейнерами
    k8s = KubernetesOperations()
    containers = ContainerOperations()

    try:
        # Запускаем контейнер с Kafka
        container = containers.start_container(
            name="kafka-container",
            image="confluentinc/cp-kafka:latest",
            ports={9092: 9092, 9093: 9093},
            environment={
                "KAFKA_ADVERTISED_LISTENERS": "PLAINTEXT://localhost:9092,PLAINTEXT_HOST://localhost:9093",
                "KAFKA_LISTENER_SECURITY_PROTOCOL_MAP": "PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT",
                "KAFKA_INTER_BROKER_LISTENER_NAME": "PLAINTEXT",
                "KAFKA_BROKER_ID": "1",
                "KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR": "1",
                "KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS": "0",
                "KAFKA_TRANSACTION_STATE_LOG_MIN_ISR": "1",
                "KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR": "1",
                "KAFKA_ZOOKEEPER_CONNECT": "zookeeper:2181",
            },
        )

        # Запускаем контейнер с Zookeeper (необходим для Kafka)
        zookeeper_container = containers.start_container(
            name="zookeeper",
            image="confluentinc/cp-zookeeper:latest",
            ports={2181: 2181},
            environment={"ZOOKEEPER_CLIENT_PORT": "2181", "ZOOKEEPER_TICK_TIME": "2000"},
        )

        if container and zookeeper_container:
            print("Ожидаем запуска контейнеров...")
            time.sleep(5)  # Даем контейнерам время на запуск

            # Ожидаем готовности Kafka в контейнере
            if containers.wait_for_kafka_ready("kafka-container", timeout=120):
                print("Kafka в контейнере готова к использованию!")
            else:
                print("Не удалось дождаться готовности Kafka в контейнере")

            # Создаем deployment в Kubernetes
            k8s.create_deployment("deployment.yaml", wait_ready=True)

            # Ищем и ожидаем готовности Kafka в поде Kubernetes по метке
            if k8s.wait_for_kafka_ready(label_selector="app=kafka", timeout=180):
                print("Kafka в поде Kubernetes готова к использованию!")
            else:
                print("Не удалось дождаться готовности Kafka в поде Kubernetes")

            # Пример выполнения команды в поде
            pod_name = k8s.get_pod_name_by_label("app=kafka")
            if pod_name:
                # Создаем тестовый топик в Kafka
                result = k8s.exec_command_in_pod(
                    pod_name=pod_name,
                    command=[
                        "/bin/sh",
                        "-c",
                        "kafka-topics.sh --create --bootstrap-server localhost:9092 --replication-factor 1 --partitions 1 --topic test-topic",
                    ],
                )
                print(f"Результат создания топика: {result}")

            print("Приложение доступно:")
            print("- Kafka в контейнере: localhost:9092")
            print("- Zookeeper: localhost:2181")
            print("Нажмите Ctrl+C для завершения...")

            while True:
                time.sleep(1)

    except KeyboardInterrupt:
        print("\nЗавершение работы...")
    finally:
        # Очистка ресурсов
        print("Очистка ресурсов...")
        k8s.cleanup()
        k8s.delete_deployment("kafka-deployment")
        containers.cleanup()


if __name__ == "__main__":
    main()
