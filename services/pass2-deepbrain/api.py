from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from graph.neo4j_client import Neo4jClient

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

    query = """
    MATCH (a)-[r]->(b)

    RETURN
        a.id AS source,
        b.id AS target,

        r.amount AS amount,

        a.status AS source_status,
        b.status AS target_status,

        a.total_volume AS source_volume,
        b.total_volume AS target_volume

    LIMIT 100
"""

    records = neo4j_client.run_query(query)

    nodes = {}
    links = []

    for record in records:

        source = record["source"]
        target = record["target"]

        nodes[source] = {
            "id": source,

            "status":
            record.get("source_status", "SAFE"),

            "volume":
                record.get("source_volume", 1)
        }

        nodes[target] = {
            "id": target,
            "status":
            record.get("target_status", "SAFE"),
            "volume":
            record.get("target_volume", 1)
        }

        links.append({
            "source": source,
            "target": target,
            "amount": record.get("amount", 0)
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

LIMIT 100
"""

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

    return [

        {
            "source": "Alice",
            "target": "Bob",
            "reason": "FROZEN ACCOUNT",
            "amount": 5000
        },

        {
            "source": "Charlie",
            "target": "Eve",
            "reason": "HIGH DENSITY NETWORK",
            "amount": 12000
        }
    ]