import asyncio
import json
import os
import time

from dotenv import load_dotenv
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from detectors.flowscope import FlowScopeDetector
from graph.neo4j_client import Neo4jClient
from detectors.velocity_detectors import detect_velocity
from detectors.mule_detector import detect_mule_accounts

load_dotenv()

DLQ_TOPIC = "transactions-restricted"
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"


# -----------------------------
# FLOWSCOPE (ASYNC HEAVY ANALYSIS)
# -----------------------------
async def run_flowscope_async(flowscope_detector, neo4j_client, txn, cache_set):

    sender = txn.get("nameOrig")
    receiver = txn.get("nameDest")
    current_step = int(txn.get("step", 1))

    loop = asyncio.get_running_loop()

    result = await loop.run_in_executor(
        None,
        flowscope_detector.analyze_flow_density,
        txn
    )

    if result:
        print("\n🌊 🕵️ FLOWSCOPE HIGH-DENSITY MALICIOUS NETWORK DETECTED")
        print(json.dumps(result, indent=4))

        if sender:
            cache_set.add(sender)
            await loop.run_in_executor(None, neo4j_client.freeze_account, sender, current_step)

        if receiver:
            cache_set.add(receiver)
            await loop.run_in_executor(None, neo4j_client.freeze_account, receiver, current_step)


# -----------------------------
# OPTIONAL: FRONTEND PUSH (SAFE STUB)
# -----------------------------
async def push_to_frontend(txn):
    """
    Sends transaction to gateway API for WebSocket broadcast.
    If gateway is down, system will NOT crash.
    """
    import httpx

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.post(
                "http://localhost:8001/push-graph",
                json={
                    "type": "NEW_TRANSACTION",
                    "data": txn
                }
            )
    except Exception as e:
        print("⚠️ Frontend push failed:", e)


# -----------------------------
# MAIN CONSUMER LOOP
# -----------------------------
async def consume():

    neo4j_client = Neo4jClient()
    flowscope = FlowScopeDetector(neo4j_client)

    LOCAL_FROZEN_CACHE = set()

    dlq_producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

    consumer = AIOKafkaConsumer(
        os.getenv("KAFKA_TOPIC_TRANSACTIONS"),
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        group_id="deepbrain-group-v2",
        auto_offset_reset="latest",
        session_timeout_ms=30000,
        max_poll_interval_ms=300000,
        max_poll_records=50
    )

    await consumer.start()
    await dlq_producer.start()

    print("🧠 DeepBrain ACTIVE — Streaming Fraud Detection Running")

    try:

        async for msg in consumer:

            txn = msg.value

            sender = txn.get("nameOrig")
            receiver = txn.get("nameDest")
            amount = txn.get("amount")

            # -----------------------------
            # GATEKEEPER (FAST CACHE + DB CHECK)
            # -----------------------------
            is_sender_frozen = (
                sender in LOCAL_FROZEN_CACHE
                or await asyncio.to_thread(neo4j_client.check_account_restriction, sender)
            )

            is_receiver_frozen = (
                receiver in LOCAL_FROZEN_CACHE
                or await asyncio.to_thread(neo4j_client.check_account_restriction, receiver)
            )

            if is_sender_frozen or is_receiver_frozen:

                frozen_party = sender if is_sender_frozen else receiver

                LOCAL_FROZEN_CACHE.add(sender)
                LOCAL_FROZEN_CACHE.add(receiver)

                print(
                    f"\n❌ [INTERDICTED] BLOCKED — "
                    f"Account {frozen_party} | Amount: {amount}"
                )

                compliance_payload = {
                    **txn,
                    "interception_type": "GATEKEEPER_RAM_CACHE",
                    "reason": f"Blocked due to frozen account: {frozen_party}",
                    "timestamp_blocked": time.time()
                }

                await dlq_producer.send_and_wait(DLQ_TOPIC, compliance_payload)
                continue

            # -----------------------------
            # NORMAL FLOW
            # -----------------------------
            print("\n📥 Transaction Received:", txn)

            await asyncio.to_thread(neo4j_client.insert_transaction, txn)

            # push to frontend (non-blocking safe)
            await push_to_frontend(txn)

            # async graph intelligence
            asyncio.create_task(
                run_flowscope_async(flowscope, neo4j_client, txn, LOCAL_FROZEN_CACHE)
            )

            # velocity detection
            velocity_result = detect_velocity(txn)
            if velocity_result:
                print("\n🚨 Velocity Fraud Detected:", velocity_result)

            # mule detection
            mule_result = detect_mule_accounts(txn)
            if mule_result:
                print("\n🚨 Mule Account Detected:", mule_result)

    except Exception as e:
        print(f"\n❌ DeepBrain Error: {e}")

    finally:
        print("\n🛑 Shutting down DeepBrain")

        neo4j_client.close()
        await consumer.stop()
        await dlq_producer.stop()


# -----------------------------
# ENTRYPOINT
# -----------------------------
if __name__ == "__main__":
    asyncio.run(consume())