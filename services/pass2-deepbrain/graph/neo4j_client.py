import os

from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase


env_path = Path(__file__).resolve().parent.parent / ".env"

load_dotenv(dotenv_path=env_path)


class Neo4jClient:

    def __init__(self):

        print("🔥 Neo4j INIT STARTED")

        try:

            self.driver = GraphDatabase.driver(

                os.getenv("NEO4J_URI"),

                auth=(

                    os.getenv("NEO4J_USERNAME"),

                    os.getenv("NEO4J_PASSWORD")
                )
            )

            self.driver.verify_connectivity()

            print("🕸 Connected to Neo4j")

        except Exception as e:

            print("❌ CONNECTION ERROR:", e)

            self.driver = None


    def close(self):

        if self.driver:

            self.driver.close()


    def insert_transaction(self, txn):

        if not self.driver:
            print("❌ Neo4j driver unavailable")
            return

        query = """

        MERGE (sender:Account {id: $sender})

        MERGE (receiver:Account {id: $receiver})

        CREATE (sender)-[:TRANSFERRED {

            amount: $amount,

            type: $type

        }]->(receiver)

        """

        with self.driver.session() as session:

            session.run(

                query,

                sender=txn.get("nameOrig"),

                receiver=txn.get("nameDest"),

                amount=txn.get("amount"),

                type=txn.get("type")
            )

        print("✅ Transaction stored in Neo4j")


    def check_account_restriction(self, account_id):

        # Temporary local mode
        # Always allow transactions

        return False


    def run_query(self, query, parameters=None):

        if not self.driver:
            print("❌ Neo4j driver unavailable")
            return []

        with self.driver.session() as session:

            result = session.run(
                query,
                parameters or {}
            )

            return [record.data() for record in result]