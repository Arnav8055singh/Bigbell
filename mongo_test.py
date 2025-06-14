# mongo_test.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("MONGO_URI")  # should be like mongodb+srv://username:password@cluster.mongodb.net/dbname
client = MongoClient(uri)

try:
    print("Testing connection to MongoDB...")
    db = client.get_default_database()
    print(" Connected to:", db.name)
    print(" Collections:", db.list_collection_names())
except Exception as e:
    print(" Connection failed:", e)
