import datetime
from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "recruitment")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "results")

mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB]
mongo_results = mongo_db[MONGO_COLLECTION]
def store_result(job_title, match):
    doc = {
        "candidate": match.get("name"),
        "score": match.get("score"),
        "status": match.get("status"),
        "email": match.get("email"),
        "job_title": job_title,
        "timestamp": datetime.datetime.utcnow()
    }
    mongo_results.insert_one(doc)