import asyncio
import httpx
import pandas as pd
import time

# Configuration
API_URL = "http://localhost:8000/transaction"
DATA_PATH = "scripts/data/paysim.csv"
BATCH_SIZE = 100 
TOTAL_LIMIT = 5000  # Start with 5k to test the waters

async def send_transaction(client, row):
    payload = {
        "step": int(row['step']),
        "type": str(row['type']),
        "amount": float(row['amount']),
        "nameOrig": str(row['nameOrig']),
        "oldbalanceOrg": float(row['oldbalanceOrg']),
        "newbalanceOrig": float(row['newbalanceOrig']),
        "nameDest": str(row['nameDest']),
        "oldbalanceDest": float(row['oldbalanceDest']),
        "newbalanceDest": float(row['newbalanceDest'])
    }
    try:
        # We use a POST to your Gateway API
        resp = await client.post(API_URL, json=payload)
        return resp.status_code
    except Exception as e:
        return f"Error: {e}"

async def run_pump():
    print(f"📂 Loading data...")
    df = pd.read_csv(DATA_PATH).head(TOTAL_LIMIT)
    
    # Increase limits for high-concurrency
    limits = httpx.Limits(max_keepalive_connections=None, max_connections=None)
    async with httpx.AsyncClient(limits=limits, timeout=None) as client:
        print(f"🚀 Pumping {TOTAL_LIMIT} transactions to the Shock Absorber...")
        start_time = time.perf_counter()

        for i in range(0, len(df), BATCH_SIZE):
            batch = df.iloc[i : i + BATCH_SIZE]
            tasks = [send_transaction(client, row) for _, row in batch.iterrows()]
            await asyncio.gather(*tasks)
            
            if i % 1000 == 0:
                print(f"📊 Progress: {i}/{TOTAL_LIMIT} sent...")

        end_time = time.perf_counter()
        duration = end_time - start_time
        print(f"\n🏁 Finished in {duration:.2f}s | Avg TPS: {TOTAL_LIMIT/duration:.2f}")

if __name__ == "__main__":
    asyncio.run(run_pump())