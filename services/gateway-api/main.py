import os
import json
import ssl
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from aiokafka import AIOKafkaProducer
from pydantic import BaseModel
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# --- SSL Configuration Helper ---
def create_ssl_context():
    """Creates a secure SSL context for Aiven Kafka."""
    context = ssl.create_default_context(cafile=os.getenv("KAFKA_CA_CERT_PATH"))
    context.load_cert_chain(
        certfile=os.getenv("KAFKA_ACCESS_CERT_PATH"),
        keyfile=os.getenv("KAFKA_ACCESS_KEY_PATH")
    )
    # Aiven often uses self-signed or specific CAs; 
    # check_hostname is usually false for Kafka URIs
    context.check_hostname = False 
    return context

# --- Lifespan Handler (The Modern way to start/stop Kafka) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global producer
    # Initialize the Producer
    producer = AIOKafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_SERVICE_URI"),
        security_protocol="SSL",
        ssl_context=create_ssl_context(),
        linger_ms=10,
        max_batch_size=65536,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    await producer.start()
    print("🚀 Kafka Producer Connected to Aiven")
    yield
    # Shutdown
    await producer.stop()
    print("🛑 Kafka Producer Stopped")

app = FastAPI(title="FinTrace Gateway API", lifespan=lifespan)

# Global Producer placeholder
producer = None

# --- Transaction Schema ---
class Transaction(BaseModel):
    step: int
    type: str
    amount: float
    nameOrig: str
    oldbalanceOrg: float
    newbalanceOrig: float
    nameDest: str
    oldbalanceDest: float
    newbalanceDest: float

@app.post("/transaction")
async def create_transaction(tx: Transaction):
    if producer is None:
        raise HTTPException(status_code=500, detail="Kafka Producer not initialized")
    try:
        await producer.send_and_wait(os.getenv("KAFKA_TOPIC_TRANSACTIONS"), tx.model_dump())
        return {"status": "accepted", "message": "Transaction queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)