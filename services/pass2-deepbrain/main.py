import asyncio
import json
import os

from dotenv import load_dotenv
from aiokafka import AIOKafkaConsumer

from detectors.flowscope import FlowScopeDetector
from graph.neo4j_client import Neo4jClient
from detectors.velocity_detectors import detect_velocity
from detectors.mule_detector import detect_mule_accounts

load_dotenv()





async def run_flowscope_async(flowscope_detector, txn):
    """
    Shifts the heavy Neo4j graph traversal out of the main Kafka thread 
    into a background executor thread, keeping ingestion blazing fast.
    """
    
    # Run the heavy Neo4j network computation in a background thread pool
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, flowscope_detector.analyze_flow_density, txn)
    
    if result:
        print("\n🌊 🕵️ FLOWSCOPE HIGH-DENSITY MALICIOUS NETWORK CAUGHT!")
        print(json.dumps(result, indent=4))


async def consume():

    neo4j_client = Neo4jClient()
    flowscope = FlowScopeDetector(neo4j_client)

    consumer = AIOKafkaConsumer(

    os.getenv("KAFKA_TOPIC_TRANSACTIONS"),

    bootstrap_servers="localhost:9092",

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
            
            sender = txn.get("nameOrig")
            receiver = txn.get("nameDest")
            amount = txn.get("amount")

            # 🛑 GATEKEEPER CHECK
            is_sender_frozen = neo4j_client.check_account_restriction(sender)
            is_receiver_frozen = neo4j_client.check_account_restriction(receiver)

            if is_sender_frozen or is_receiver_frozen:

                frozen_party = sender if is_sender_frozen else receiver

                print(
                    f"\n❌ [INTERDICTED] Transaction dropped! "
                    f"Account {frozen_party} is FROZEN. "
                    f"Blocked transfer of {amount}"
                )

                continue

            print("\n📥 Transaction Received")
            print(txn)

            # Store transaction in Neo4j
            await asyncio.to_thread(neo4j_client.insert_transaction, txn)

            # Run FlowScope Graph Topology Check
            # flowscope_result = flowscope.analyze_flow_density(txn)

            # Run flowscope asynchronously 
            asyncio.create_task(run_flowscope_async(flowscope, txn))


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