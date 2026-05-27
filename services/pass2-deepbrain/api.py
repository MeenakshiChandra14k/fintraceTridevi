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
    RETURN a, r, b
    LIMIT 100
    """

    records = neo4j_client.run_query(query)

    nodes = {}
    links = []

    for record in records:

        a = record["a"]
        b = record["b"]
        r = record["r"]

        a_id = str(a.get("id", a.element_id))
        b_id = str(b.get("id", b.element_id))

        nodes[a_id] = {
            "id": a_id,
            "risk": a.get("risk", 0)
        }

        nodes[b_id] = {
            "id": b_id,
            "risk": b.get("risk", 0)
        }

        links.append({
            "source": a_id,
            "target": b_id,
            "amount": r.get("amount", 0)
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

    RETURN
      a.id AS account,
      a.risk AS risk,
      a.status AS status,
      a.freeze_reason AS freeze_reason,
      collect({
        target: b.id,
        amount: t.amount,
        type: t.type
      }) AS outgoing
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

    query = f"""
    MATCH (a)-[r]->(b)
    WHERE a.id = '{account_id}' OR b.id = '{account_id}'
    RETURN a, r, b
    LIMIT 50
    """

    records = neo4j_client.run_query(query)

    nodes = {}
    links = []

    for record in records:

        a = record["a"]
        b = record["b"]

        a_id = str(a.get("id", a.element_id))
        b_id = str(b.get("id", b.element_id))

        nodes[a_id] = {
            "id": a_id,
            "risk": a.get("risk", 0)
        }

        nodes[b_id] = {
            "id": b_id,
            "risk": b.get("risk", 0)
        }

        links.append({
            "source": a_id,
            "target": b_id
        })

    return {
        "nodes": list(nodes.values()),
        "links": links
    }