import json
import time
from aiokafka import AIOKafkaProducer
import asyncio

KAFKA_TOPIC = "transactions"
KAFKA_BOOTSTRAP = "localhost:9092"


async def send():
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

    await producer.start()

    try:
        while True:

            txn = {
                "nameOrig": "A100",
                "nameDest": "B200",
                "amount": 5000
            }

            await producer.send_and_wait(KAFKA_TOPIC, txn)

            print("📤 Sent:", txn)

            time.sleep(3)

    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(send())