import os
import json
import httpx
import asyncio


from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from aiokafka import AIOKafkaProducer
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import WebSocket, WebSocketDisconnect


GATEWAY_PUSH_URL = "http://localhost:8001/push-graph"

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):

    global producer

    producer = AIOKafkaProducer(
        bootstrap_servers="localhost:9092",
        linger_ms=10,
        max_batch_size=65536,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

    await producer.start()

    print("🚀 Kafka Producer Connected")

    yield

    await producer.stop()

    print("🛑 Kafka Producer Stopped")


app = FastAPI(
    title="FinTrace Gateway API",
    lifespan=lifespan
)

producer = None


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
        raise HTTPException(
            status_code=500,
            detail="Kafka Producer not initialized"
        )

    try:

        await producer.send_and_wait(
            os.getenv("KAFKA_TOPIC_TRANSACTIONS"),
            tx.model_dump()
        )

        return {
            "status": "accepted",
            "message": "Transaction queued"
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/graph")
async def graph_stream(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            # keep connection alive
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/push-graph")
async def push_graph(data: dict):
    await manager.broadcast(data)
    return {"status": "broadcasted"}

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )