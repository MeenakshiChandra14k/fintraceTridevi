import os
from graph.neo4j_client import Neo4jClient

class FlowScopeDetector:
    def __init__(self, neo4j_client: Neo4jClient):
        self.client = neo4j_client

    def analyze_flow_density(self, txn: dict, hop_limit: int = 3) -> dict:
        """
        Analyzes the network structure around the sender/receiver of a transaction.
        Returns a suspicious structural density score based on closed loops and fan-outs.
        """
        sender = txn.get("nameOrig")
        receiver = txn.get("nameDest")
        
        # Cypher query to count paths, unique accounts, and total volume within N hops
        query = """
        MATCH path = (src:Account)-[r:TRANSFERRED*1..2]-(dst:Account)
        WHERE src.id = $sender OR src.id = $receiver
        WITH count(path) AS total_paths, 
             collect(distinct dst.id) AS target_accounts,
             sum(reduce(s = 0, x IN r | s + x.amount)) AS total_volume
        RETURN total_paths, size(target_accounts) AS unique_destinations, total_volume
        """
        
        try:
            with self.client.driver.session() as session:
                result = session.run(query, sender=sender, receiver=receiver)
                record = result.single()
                
                if not record:
                    return None
                    
                total_paths = record["total_paths"]
                unique_dests = record["unique_destinations"]
                total_volume = record["total_volume"]
                
                # FlowScope Logic: If paths vastly exceed unique destinations, money is looping/clustering
                density_ratio = total_paths / max(unique_dests, 1)

                # 📊 LIVE HEARTBEAT LOG (So you know it's calculation-active!)
                print(f"📊 [FlowScope Trace] Paths Found: {total_paths} | Unique Accounts: {unique_dests} | Density Ratio: {density_ratio:.2f}")
                
                # Flag as anomaly if the subgraph structure is too tight/dense
                if density_ratio > 1.5 and total_paths > 2:

                    #free the account (dhfl case)
                    freeze_query = """
                    MATCH (a:Account)
                    WHERE a.id = $sender OR a.id = $receiver
                    SET a.status = "FROZEN", 
                        a.freeze_reason = "FlowScope High Density Subgraph Anomaly",
                        a.frozen_at = timestamp()
                    RETURN a.id as blocked_id
                    """

                    try:
                        with self.client.driver.session() as block_session:
                            block_session.run(freeze_query, sender=sender, receiver=receiver)
                            print(f"🔒 [SHIELD ENGAGED] Automatically froze high-risk routing nodes: {sender} & {receiver}")
                    except Exception as block_err:
                        print(f"⚠️ Shield execution error: {block_err}")

                    return {
                        "alert": "FlowScope Dense Subgraph Detected",
                        "sender": sender,
                        "receiver": receiver,
                        "density_ratio": round(density_ratio, 2),
                        "total_paths_in_cluster": total_paths,
                        "tracked_volume": round(total_volume, 2)
                    }
        except Exception as e:
            print(f"⚠️ FlowScope analysis error: {e}")
            
        return None