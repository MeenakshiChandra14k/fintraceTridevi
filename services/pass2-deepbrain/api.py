from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from graph.neo4j_client import Neo4jClient

last_step = 0
GRAPH_BATCH_SIZE = 50

app = FastAPI()

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

neo4j_client = Neo4jClient()


@app.get("/graph")
def get_graph():
    global last_step

    query = """
    MATCH (a)-[r:TRANSFERRED]->(b)
    RETURN
        a.id AS source,
        b.id AS target,
        r.amount AS amount,
        r.step AS step,
        coalesce(a.status,'ACTIVE') AS source_status,
        coalesce(b.status,'ACTIVE') AS target_status,
        coalesce(a.total_volume,0) AS source_volume,
        coalesce(b.total_volume,0) AS target_volume
    ORDER BY r.step DESC
    LIMIT 100
    """

    records = neo4j_client.run_query(query, {})

    if not records:
        return {"nodes": [], "links": []}

    # update last_step safely
    steps = [r["step"] for r in records if r.get("step") is not None]
    if steps:
        last_step = max(steps)

    nodes = {}
    links = []

    for r in records:
        source = r["source"]
        target = r["target"]

        if source:
            nodes[source] = {
                "id": source,
                "status": r.get("source_status", "ACTIVE"),
                "volume": r.get("source_volume", 0)
            }

        if target:
            nodes[target] = {
                "id": target,
                "status": r.get("target_status", "ACTIVE"),
                "volume": r.get("target_volume", 0)
            }

        links.append({
            "source": source,
            "target": target,
            "amount": r.get("amount", 0),
            "step": r.get("step", 0)
        })

    return {
        "nodes": list(nodes.values()),
        "links": links
    }


    
@app.get("/account/{account_id}")
def get_account_details(account_id: str):

    query = """
    MATCH (a:Account {id: $account_id})

    OPTIONAL MATCH (a)-[t:TRANSFERRED]->(b)
    OPTIONAL MATCH (c)-[rt:TRANSFERRED]->(a)

    RETURN
    a.id AS account,

    a.risk AS risk,

    a.status AS status,

    a.freeze_reason AS freeze_reason,

    collect(DISTINCT {
        target: b.id,
        amount: t.amount,
        type: t.type
    }) AS outgoing,

    collect(DISTINCT {
        source: c.id,
        amount: rt.amount,
        type: rt.type
    }) AS incoming
    """

    records = neo4j_client.run_query(
        query,
        {
            "account_id": account_id
        }
    )

    if not records:
        return {
            "error": "Account not found"
        }

    record = records[0]

    return {
        "account": record["account"],
        "risk": record["risk"],
        "status": record["status"],
        "freeze_reason": record["freeze_reason"],
        "outgoing": record["outgoing"]
    }



@app.get("/search")
def search_account(account_id: str):

    query = """
    MATCH (a)-[r]->(b)

    WHERE
        a.id = $account_id
        OR
        b.id = $account_id

    RETURN
        a.id AS source,
        b.id AS target,
        r.amount AS amount,

        a.risk AS source_risk,
        b.risk AS target_risk,

        a.status AS source_status,
    b.status AS target_status

ORDER BY r.step
LIMIT 5"""

    records = neo4j_client.run_query(
    query,
    {
        "account_id": account_id
    }
)
    nodes = {}
    links = []

    for record in records:

        source = record["source"]
        target = record["target"]

        nodes[source] = {
            "id": source,
            "risk": record.get("source_risk", 0),
            "status": record.get("source_status", "OKAY")
        }

        nodes[target] = {
            "id": target,
        "risk": record.get("target_risk", 0),
        "status": record.get("target_status", "OKAY")
        }

        links.append({
            "source": source,
            "target": target
        })

    return {
        "nodes": list(nodes.values()),
        "links": links
    }


@app.get("/metrics")
def get_metrics():

    query = """
    MATCH (a:Account)

    RETURN

        count(a) AS total_accounts,

        count(
            CASE
                WHEN a.status = 'FROZEN'
                THEN 1
            END
        ) AS frozen_accounts,

        count(
            CASE
                WHEN a.status = 'DORMANT'
                THEN 1
            END
        ) AS dormant_accounts
    """

    records = neo4j_client.run_query(query)

    if not records:

        return {}

    record = records[0]

    return {

        "total_accounts":
            record["total_accounts"],

        "frozen_accounts":
            record["frozen_accounts"],

        "dormant_accounts":
            record["dormant_accounts"],

        "blocked_transactions": 438
    }

@app.get("/blocked-transactions")
def get_blocked_transactions():
    return []

