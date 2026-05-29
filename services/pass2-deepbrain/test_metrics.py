import os
import json
from pathlib import Path
from dotenv import load_dotenv

# 🎯 Explicitly target the root directory where your .env lives
# Current: services/pass2-deepbrain -> Parent: services -> Parent.Parent: root (fintraceTridevi)
root_dir = Path(__file__).resolve().parent.parent.parent
env_path = root_dir / ".env"

print(f"🔍 Hard-seeking .env at: {env_path.resolve()}")

if env_path.exists():
    print("✅ .env file physically found!")
    load_dotenv(dotenv_path=env_path)
else:
    print("❌ ERROR: Still missing. Let's look up one more level just in case.")
    # Fallback just in case execution context shifts
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

# Now import your client *after* variables are fully populated
from graph.neo4j_client import Neo4jClient

def run_metric_check():
    # Print out what Neo4j credentials got loaded
    uri = os.getenv("NEO4J_URI") or os.getenv("GRAPH_URI")
    print(f"📊 Connecting to Neo4j Graph Engine at: {uri}...")
    
    if not uri:
        print("⚠️ CRITICAL: Environment variables loaded, but credentials are still empty!")
        return
        
    client = Neo4jClient()
    
    try:
        print("🔍 Computing real-time node state distributions...")
        stats = client.get_system_overview()
        
        print("\n📈 CURRENT LIVE METRICS FOR FRONTEND CONTRACT:")
        print(json.dumps(stats, indent=4))
        
    except Exception as e:
        print(f"❌ Metrics Error: {e}")
    finally:
        if 'client' in locals() and hasattr(client, 'driver') and client.driver is not None:
            client.close()
        print("\n🔌 Neo4j connection safely closed.")

if __name__ == "__main__":
    run_metric_check()