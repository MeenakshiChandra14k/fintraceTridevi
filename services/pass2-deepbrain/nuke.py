import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
driver = GraphDatabase.driver(os.getenv("NEO4J_URI"), auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")))

with driver.session() as session:
    print("⚠️  Nuking Neo4j Aura data...")
    res = session.run("MATCH (n) DETACH DELETE n").consume()
    print(f"💥 Done! Deleted {res.counters.nodes_deleted} nodes.")
driver.close()
