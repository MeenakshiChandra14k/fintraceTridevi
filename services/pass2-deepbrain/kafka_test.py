import asyncio
import json
import os

from dotenv import load_dotenv
from aiokafka import AIOKafkaConsumer

load_dotenv()



async def consume():

    topic = os.getenv("KAFKA_TOPIC_TRANSACTIONS")
    kafka_uri = os.getenv("KAFKA_SERVICE_URI")

    print("\n📡 Kafka Configuration")
    print(f"Topic: {topic}")
    print(f"Kafka URI: {kafka_uri}")

    if not topic:
        raise ValueError("❌ KAFKA_TOPIC_TRANSACTIONS missing")

    if not kafka_uri:
        raise ValueError("❌ KAFKA_SERVICE_URI missing")

    consumer = AIOKafkaConsumer(

    topic,

    bootstrap_servers="localhost:9092",

        value_deserializer=lambda m: json.loads(
            m.decode("utf-8")
        ),

        group_id="deepbrain-test-group"
    )

    print("\n⏳ Connecting to Kafka...")

    await consumer.start()

    print("🧠 Connected to Kafka")

    try:

        async for msg in consumer:

            print("\n📥 MESSAGE RECEIVED:")
            print(msg.value)

    except Exception as e:

        print(f"\n❌ Kafka Consumer Error: {e}")

    finally:

        print("\n🛑 Closing Kafka Consumer")

        await consumer.stop()


if __name__ == "__main__":

    try:

        asyncio.run(consume())

    except Exception as e:

        print(f"\n🔥 FATAL ERROR: {e}")