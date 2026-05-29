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

    def get_system_overview(self):

        if not self.driver:
            return {}
        
        query = """
        MATCH (a:Account)
        WITH 
            count(a) as total_nodes,
            sum(CASE WHEN a.status = 'FROZEN' THEN 1 ELSE 0 END) as frozen_count,
            sum(CASE WHEN a.status = 'DORMANT' THEN 1 ELSE 0 END) as dormant_count,
            sum(CASE WHEN a.status IS NULL OR a.status = 'OK' THEN 1 ELSE 0 END) as okay_count

        OPTIONAL MATCH (f:Account {status: 'FROZEN'})
            
        WITH total_nodes, frozen_count, dormant_count, okay_count, f,
             coalesce(f.current_balance, 0.0) as locked_vault_cash

        OPTIONAL MATCH (f)<-[r:TRANSFERRED]-()

        WITH total_nodes, frozen_count, dormant_count, okay_count,
             sum(locked_vault_cash) as total_vault_hold,
             
             // Lost: Money that hit the node BEFORE the system flagged it
             sum(CASE WHEN f.step_frozen IS NOT NULL AND r.step < f.step_frozen THEN r.amount ELSE 0 END) as lost_traffic,
             
             // Secured Traffic: Flowing money intercepted AFTER or AT the freeze step
             sum(CASE WHEN f.step_frozen IS NOT NULL AND r.step >= f.step_frozen THEN r.amount ELSE 0 END) as secured_traffic
        
        RETURN total_nodes, frozen_count, dormant_count, okay_count, total_vault_hold, lost_traffic, secured_traffic
        """
        with self.driver.session() as session:
            result = session.run(query).single()
            if result:
                secured_pool = (result["secured_traffic"] or 0.0) + (result["total_vault_hold"] or 0.0)

                return {
                    "total_accounts": result["total_nodes"],
                    "frozen_accounts": result["frozen_count"],
                    "dormant_accounts": result["dormant_count"],
                    "okay_accounts": result["okay_count"],  # Fixed the syntax error here
                    "secured_funds_pool": round(secured_pool, 2),
                    "lost_funds_pool": round(result["lost_traffic"] or 0.0, 2)
                }

    def insert_transaction(self, txn):

        if not self.driver:
            print("❌ Neo4j driver unavailable")
            return

        query = """

        MERGE (sender:Account {id: $sender})
        ON CREATE SET sender.current_balance = $old_bal_orig
        ON MATCH SET sender.current_balance = $new_bal_orig

        MERGE (receiver:Account {id: $receiver})
        ON CREATE SET receiver.current_balance = $old_bal_dest + $amount
        ON MATCH SET receiver.current_balance = $new_bal_dest

        CREATE (sender)-[:TRANSFERRED {

            amount: $amount,
            type: $type,
            step: $step

        }]->(receiver)

        """

        with self.driver.session() as session:

            session.run(

                query,

                sender=txn.get("nameOrig"),
                receiver=txn.get("nameDest"),
                amount=txn.get("amount"),
                type=txn.get("type"),
                step=int(txn.get("step", 1)),
                old_bal_orig=float(txn.get("oldbalanceOrg", 0)),
                new_bal_orig=float(txn.get("newbalanceOrig", 0)),
                old_bal_dest=float(txn.get("oldbalanceDest", 0)),
                new_bal_dest=float(txn.get("newbalanceDest", 0))
            )

        print(f"✅ Transaction stored in Neo4j (Step {txn.get('step')})")

    def freeze_account(self, account_id, current_step):
        """
        Binds a restriction state to an account node with timestamp checkpoints.
        """
        if not self.driver:
            return
            
        query = """
        MATCH (a:Account {id: $account_id})
        SET a.status = 'FROZEN',
            a.step_frozen = $current_step
        """
        with self.driver.session() as session:
            session.run(query, account_id=account_id, current_step=int(current_step))
        print(f"🔒 Account {account_id} locked down permanently at step {current_step}")

    def close(self):
        if self.driver:
            self.driver.close()

    def check_account_restriction(self, account_id):

        # Temporary local mode
        # Always allow transactions

        return False