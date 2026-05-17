import asyncio
import json
import ssl
import os

from dotenv import load_dotenv
from aiokafka import AIOKafkaConsumer

from detectors.flowscope import FlowScopeDetector
from graph.neo4j_client import Neo4jClient
from detectors.velocity_detectors import detect_velocity
from detectors.mule_detector import detect_mule_accounts

load_dotenv()


def create_ssl_context():

    context = ssl.create_default_context(
        cafile=os.getenv("KAFKA_CA_CERT_PATH")
    )

    context.load_cert_chain(
        certfile=os.getenv("KAFKA_ACCESS_CERT_PATH"),
        keyfile=os.getenv("KAFKA_ACCESS_KEY_PATH")
    )

    context.check_hostname = False

    return context


async def consume():

    neo4j_client = Neo4jClient()
    flowscope = FlowScopeDetector(neo4j_client)

    consumer = AIOKafkaConsumer(

        os.getenv("KAFKA_TOPIC_TRANSACTIONS"),

        bootstrap_servers=os.getenv("KAFKA_SERVICE_URI"),

        security_protocol="SSL",

        ssl_context=create_ssl_context(),

        value_deserializer=lambda m: json.loads(
            m.decode("utf-8")
        ),

        group_id="deepbrain-group-v2",

        auto_offset_reset="latest",

        session_timeout_ms=30000,   # Give the brain 30s to talk to the cloud before failing
        max_poll_interval_ms=300000, # Allow up to 5 minutes to process a batch of data
        max_poll_records=50         # Pull smaller batches so Neo4j doesn't queue up too high

    )

    await consumer.start()

    print("🧠 DeepBrain Connected to Kafka")

    try:

        async for msg in consumer:

            txn = msg.value

            print("\n📥 Transaction Received")
            print(txn)

            # Store transaction in Neo4j
            await asyncio.to_thread(neo4j_client.insert_transaction, txn)

            # Run FlowScope Graph Topology Check
            flowscope_result = flowscope.analyze_flow_density(txn)
            if flowscope_result:
                print("\n🌊 🕵️ FLOwSCOPE HIGH-DENSITY MALICIOUS NETWORK CAUGHT!")
                print(flowscope_result)

            # Run velocity detection
            velocity_result = detect_velocity(txn)

            if velocity_result:

                print("\n🚨 Velocity Fraud Detected")
                print(velocity_result)

            # Run mule account detection
            mule_result = detect_mule_accounts(txn)

            if mule_result:

                print("\n🚨 Mule Account Detected")
                print(mule_result)

    except Exception as e:

        print(f"\n❌ DeepBrain Error: {e}")

    finally:

        print("\n🛑 Shutting down DeepBrain")

        neo4j_client.close()

        await consumer.stop()


if __name__ == "__main__":

    asyncio.run(consume())