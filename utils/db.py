from pymongo import MongoClient
from config import MONGO_DB_NAME, MONGO_URI

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=1500)
db = client[MONGO_DB_NAME]
