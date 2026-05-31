import asyncio
import json
import os
import logging
import time

from dotenv import load_dotenv
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from detectors.flowscope import FlowScopeDetector
from graph.neo4j_client import Neo4jClient
from detectors.velocity_detectors import detect_velocity
from detectors.mule_detector import detect_mule_accounts

load_dotenv()

DLQ_TOPIC = "transactions-restricted"
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
BLOCKED_TRANSACTIONS_DLQ = []
LOCAL_FROZEN_CACHE = set()

neo4j_client = Neo4jClient()
flowscope = FlowScopeDetector(neo4j_client)

app = FastAPI(title="FinTrace SOC API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(consume())

async def run_flowscope_async(flowscope_detector, neo4j_client, txn, cache_set):
    sender = txn.get("nameOrig")
    receiver = txn.get("nameDest")
    current_step = int(txn.get("step", 1))

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, flowscope_detector.analyze_flow_density, txn)
    
    if result:
        print("\n🌊 🕵️ FLOWSCOPE HIGH-DENSITY MALICIOUS NETWORK CAUGHT!")
        print(json.dumps(result, indent=4))

        if sender:
            cache_set.add(sender)
        if receiver:
            cache_set.add(receiver)

        if sender:
            await loop.run_in_executor(None, neo4j_client.freeze_account, sender, current_step)
        if receiver:
            await loop.run_in_executor(None, neo4j_client.freeze_account, receiver, current_step)

async def consume():
    global LOCAL_FROZEN_CACHE, BLOCKED_TRANSACTIONS_DLQ

    dlq_producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

    consumer = AIOKafkaConsumer(
        os.getenv("KAFKA_TOPIC_TRANSACTIONS"),
        bootstrap_servers="localhost:9092",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        group_id="deepbrain-group-v2",
        auto_offset_reset="latest",
        session_timeout_ms=30000,   
        max_poll_interval_ms=300000, 
        max_poll_records=50         
    )

    await consumer.start()
    await dlq_producer.start()

    print("🧠 DeepBrain Connected to Kafka and Compliance DLQ Engine Active")

    try:
        async for msg in consumer:
            txn = msg.value
            
            sender = txn.get("nameOrig")
            receiver = txn.get("nameDest")
            amount = txn.get("amount")

            is_sender_frozen = sender in LOCAL_FROZEN_CACHE or await asyncio.to_thread(neo4j_client.check_account_restriction, sender)
            is_receiver_frozen = receiver in LOCAL_FROZEN_CACHE or await asyncio.to_thread(neo4j_client.check_account_restriction, receiver)

            if is_sender_frozen or is_receiver_frozen:
                frozen_party = sender if is_sender_frozen else receiver

                LOCAL_FROZEN_CACHE.add(sender)
                LOCAL_FROZEN_CACHE.add(receiver)

                print(
                    f"\n❌ [INTERDICTED] Transaction dropped instantly by Gatekeeper Cache! "
                    f"Account {frozen_party} is FROZEN. "
                    f"Blocked transfer of {amount}"
                )

                compliance_payload = {
                    **txn,
                    "interception_type": "GATEKEEPER_RAM_CACHE",
                    "reason": f"Transaction blocked. Account {frozen_party} is permanently locked down in memory shield.",
                    "timestamp_blocked": time.time()
                }

                BLOCKED_TRANSACTIONS_DLQ.insert(0, {
                    "source": sender,
                    "target": receiver,
                    "amount": amount,
                    "reason": compliance_payload["reason"]
                })
                if len(BLOCKED_TRANSACTIONS_DLQ) > 30:
                    BLOCKED_TRANSACTIONS_DLQ.pop()

                await dlq_producer.send_and_wait(DLQ_TOPIC, compliance_payload)
                continue

            print("\n📥 Transaction Received")
            print(txn)

            await asyncio.to_thread(neo4j_client.insert_transaction, txn)
            asyncio.create_task(run_flowscope_async(flowscope, neo4j_client, txn, LOCAL_FROZEN_CACHE))

            velocity_result = detect_velocity(txn)
            if velocity_result:
                print("\n🚨 Velocity Fraud Detected")
                print(velocity_result)

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
        await dlq_producer.stop()

@app.get("/api/metrics")
async def get_metrics():
    try:
        total_accounts = neo4j_client.get_total_accounts_count()
        frozen_accounts = neo4j_client.get_frozen_accounts_count()
    except AttributeError:
        total_accounts = 2500
        frozen_accounts = len(LOCAL_FROZEN_CACHE)

    secured_funds = sum(float(tx["amount"]) for tx in BLOCKED_TRANSACTIONS_DLQ)
    return {
        "frozen_accounts": frozen_accounts,
        "total_accounts": total_accounts,
        "blocked_transactions": len(BLOCKED_TRANSACTIONS_DLQ),
        "secured_funds_pool": secured_funds,
        "lost_funds_pool": 0,
        "okay_accounts": max(0, total_accounts - frozen_accounts)
    }

@app.get("/api/graph")
async def get_graph():
    try:
        records = neo4j_client.get_active_graph_projection()
        return records
    except AttributeError:
        return {
            "nodes": [{"id": node_id, "status": "FROZEN", "volume": 75000, "risk": 95} for node_id in LOCAL_FROZEN_CACHE] or [
                {"id": "C10874", "status": "ACTIVE", "volume": 15000, "risk": 10}
            ],
            "links": []
        }

@app.get("/api/blocked-transactions")
async def get_blocked_transactions():
    return BLOCKED_TRANSACTIONS_DLQ

@app.get("/api/search")
async def search_account(account_id: str = Query(..., alias="account_id")):
    is_restricted = account_id in LOCAL_FROZEN_CACHE or neo4j_client.check_account_restriction(account_id)
    return {
        "nodes": [{"id": account_id, "status": "FROZEN" if is_restricted else "ACTIVE", "volume": 45000, "risk": 95 if is_restricted else 5}],
        "links": []
    }

@app.get("/api/account/{account_id}")
async def get_account_details(account_id: str):
    is_restricted = account_id in LOCAL_FROZEN_CACHE or neo4j_client.check_account_restriction(account_id)
    return {
        "account": account_id,
        "status": "FROZEN" if is_restricted else "ACTIVE",
        "risk": 95 if is_restricted else 5,
        "freeze_reason": "High-density flow structure detection." if is_restricted else "None"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8001, reload=True)