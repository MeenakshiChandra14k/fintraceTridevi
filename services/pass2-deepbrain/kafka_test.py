import asyncio
import json
import ssl
import os

from dotenv import load_dotenv
from aiokafka import AIOKafkaConsumer

load_dotenv()


def create_ssl_context():

    ca_path = os.getenv("KAFKA_CA_CERT_PATH")
    cert_path = os.getenv("KAFKA_ACCESS_CERT_PATH")
    key_path = os.getenv("KAFKA_ACCESS_KEY_PATH")

    print("\n🔐 SSL Configuration")
    print(f"CA Path: {ca_path}")
    print(f"Cert Path: {cert_path}")
    print(f"Key Path: {key_path}")

    # Verify files exist before loading
    for path in [ca_path, cert_path, key_path]:

        if not path:
            raise ValueError(f"❌ Missing env variable for SSL path: {path}")

        if not os.path.exists(path):
            raise FileNotFoundError(
                f"❌ File not found: {path}"
            )

    print("✅ SSL certificate files found")

    context = ssl.create_default_context(
        cafile=ca_path
    )

    context.load_cert_chain(
        certfile=cert_path,
        keyfile=key_path
    )

    context.check_hostname = False

    print("✅ SSL context created")

    return context


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

        bootstrap_servers=kafka_uri,

        security_protocol="SSL",

        ssl_context=create_ssl_context(),

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