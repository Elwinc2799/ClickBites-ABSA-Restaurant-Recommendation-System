from pymongo import MongoClient
from config import MONGO_URI, MONGO_PORT, MONGO_TIMEOUT

# Singleton class for MongoDB connection
class Database:
    __instance = None

    @staticmethod
    def get_instance():
        if Database.__instance == None:
            Database()
        return Database.__instance

    def __init__(self):
        if Database.__instance != None:
            raise Exception("Database connection already exists")
        else:
            try:
                self.client = MongoClient(MONGO_URI, port=MONGO_PORT, serverSelectionTimeoutMS=MONGO_TIMEOUT)
                self.client.server_info()
                print("Connected to MongoDB")
                Database.__instance = self
            except Exception as e:
                print(e)
                print("Could not connect to MongoDB")

    def get_db(self, db_name):
        return self.client.ckbt_db[db_name]
