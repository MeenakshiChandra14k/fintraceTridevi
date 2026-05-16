from dotenv import load_dotenv
import os

print("Loading env...")

load_dotenv()

print("URI:", os.getenv("NEO4J_URI"))
print("USER:", os.getenv("NEO4J_USERNAME"))
print("PASSWORD:", os.getenv("NEO4J_PASSWORD"))
print("DATABASE:", os.getenv("NEO4J_DATABASE"))