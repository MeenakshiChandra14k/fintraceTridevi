import asyncio
import json
import os
import logging
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

# New additions for API serving
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

# Global tracking references so the API can read them instantly
BLOCKED_TRANSACTIONS_DLQ = []
LOCAL_FROZEN_CACHE = set()

# --- MODERN LIFESPAN MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(consume())
    yield
    task.cancel()

# Initialize API Gateway
app = FastAPI(title="FinTrace SOC API Gateway", lifespan=lifespan)

# Enable CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



async def run_flowscope_async(flowscope_detector, neo4j_client, txn, cache_set):
    """
    Shifts the heavy Neo4j graph traversal out of the main Kafka thread 
    into a background executor thread, keeping ingestion blazing fast.
    """
    
    sender = txn.get("nameOrig")
    receiver = txn.get("nameDest")
    current_step = int(txn.get("step", 1))

    # Run the heavy Neo4j network computation in a background thread pool
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, flowscope_detector.analyze_flow_density, txn)

    
    if result:
        print("\n🌊 🕵️ FLOWSCOPE HIGH-DENSITY MALICIOUS NETWORK CAUGHT!")
        print(json.dumps(result, indent=4))

        #local RAM - cache
        if sender:
            cache_set.add(sender)
        if receiver:
            cache_set.add(receiver)


        if sender:
            await loop.run_in_executor(None, neo4j_client.freeze_account, sender, current_step)
        if receiver:
            await loop.run_in_executor(None, neo4j_client.freeze_account, receiver, current_step)


def calculate_dynamic_risk(amount, flowscope_result=None):
    """
    Calculates risk: Base risk (amount) + Multipliers for detected anomalies.
    """
    base_risk = min(float(amount) / 1000, 50)  # Volume factor (max 50 points)
    anomaly_factor = 45 if flowscope_result else 0 # Topology risk (45 points)
    
    total_risk = min(int(base_risk + anomaly_factor + 5), 99) # +5 for "inherent risk"
    return total_risk

async def consume():

    global LOCAL_FROZEN_CACHE, BLOCKED_TRANSACTIONS_DLQ

    neo4j_client = Neo4jClient()
    flowscope = FlowScopeDetector(neo4j_client)

    #LOCAL_FROZEN_CACHE = set()

    # Dead-Letter Queue (DLQ) Producer

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

        session_timeout_ms=30000,   # Give the brain 30s to talk to the cloud before failing
        max_poll_interval_ms=300000, # Allow up to 5 minutes to process a batch of data
        max_poll_records=50         # Pull smaller batches so Neo4j doesn't queue up too high

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

            # 🛑 GATEKEEPER CHECK
            #is_sender_frozen = neo4j_client.check_account_restriction(sender)
            #is_receiver_frozen = neo4j_client.check_account_restriction(receiver)

            # 🛑 GATEKEEPER CHECK (Fixed to run asynchronously)
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

                risk_score = calculate_dynamic_risk(amount, flowscope_result=True)

                # DLQ payload for frontend
                compliance_payload = {
                    **txn,
                    "interception_type": "GATEKEEPER_RAM_CACHE",
                    "reason": f"Transaction blocked. Account {frozen_party} is permanently locked down in memory shield.",
                    "risk": risk_score,
                    "timestamp_blocked": time.time()
                }

                # Push to our live array so the UI can display it
                BLOCKED_TRANSACTIONS_DLQ.insert(0, {
                    "source": sender,
                    "target": receiver,
                    "amount": amount,
                    "reason": compliance_payload["reason"],
                    "risk": risk_score
                })
                if len(BLOCKED_TRANSACTIONS_DLQ) > 40:
                    BLOCKED_TRANSACTIONS_DLQ.pop()

                #send to kafka topic without blocking ingestion - asynchronous
                await dlq_producer.send_and_wait(DLQ_TOPIC, compliance_payload)

                continue

            print("\n📥 Transaction Received")
            print(txn)

            # Store transaction in Neo4j
            await asyncio.to_thread(neo4j_client.insert_transaction, txn)

            # Run FlowScope Graph Topology Check
            # flowscope_result = flowscope.analyze_flow_density(txn)

            # Run flowscope asynchronously 
            asyncio.create_task(run_flowscope_async(flowscope, neo4j_client, txn, LOCAL_FROZEN_CACHE))


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

        await dlq_producer.stop()


# Runs consume loop in the background as a non blocking task when FastAPI starts up
@app.get("/api/metrics")
async def get_metrics():
    return {
        "frozen_accounts": len(LOCAL_FROZEN_CACHE),
        "blocked_transactions": len(BLOCKED_TRANSACTIONS_DLQ),
    }


@app.get("/api/graph")
async def get_graph():
    # Construct a clean topology visualization using active session events
    nodes_map = {}
    links_list = []
    
    for tx in BLOCKED_TRANSACTIONS_DLQ:
        s, t, a, r = tx.get("source"), tx.get("target"), tx.get("amount"), tx.get("risk",0)
        if s and t:
            nodes_map[s] = {"id": s, "status": "BLOCKED", "volume": a, "risk": r}
            nodes_map[t] = {"id": t, "status": "SAFE", "volume": a, "risk": 15}
            links_list.append({"source": s, "target": t, "amount": a})
            
    return {"nodes": list(nodes_map.values()), "links": links_list}

@app.get("/api/blocked-transactions")
async def get_blocked_transactions():
    # Returns the live rolling history array to feed the compliance log layout
    return BLOCKED_TRANSACTIONS_DLQ


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8001, reload=True)
    #asyncio.run(consume())