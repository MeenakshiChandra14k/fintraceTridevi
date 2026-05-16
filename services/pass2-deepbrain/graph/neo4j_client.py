from neo4j import GraphDatabase

from dotenv import load_dotenv
import os

load_dotenv()


class Neo4jClient:

    def __init__(self):

        self.driver = GraphDatabase.driver(

            os.getenv("NEO4J_URI"),

            auth=(
                os.getenv("NEO4J_USER"),
                os.getenv("NEO4J_PASSWORD")
            )
        )

        self.database = os.getenv("NEO4J_DATABASE")

    def close(self):

        self.driver.close()

    def insert_transaction(self, txn):

        query = """

        MERGE (sender:Account {
            id: $sender
        })

        MERGE (receiver:Account {
            id: $receiver
        })

        CREATE (sender)-[:TRANSFER {
            amount: $amount,
            type: $type,
            step: $step
        }]->(receiver)

        """

        with self.driver.session(
            database=self.database
        ) as session:

            session.run(

                query,

                sender=txn["nameOrig"],
                receiver=txn["nameDest"],

                amount=txn["amount"],
                type=txn["type"],
                step=txn["step"]
            )

            print(
                f"✅ Inserted transaction: "
                f"{txn['nameOrig']} -> {txn['nameDest']}"
            )