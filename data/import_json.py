import json
from pymongo import MongoClient, InsertOne
import os
import random

client = MongoClient("mongodb+srv://xxx:xxx@cluster0.mkcvmve.mongodb.net/")        # Use your created mongodb cluster URI
db = client.ckbt_db2

# List of collections and corresponding file paths
collections_files = [
    ("business", "./data/business.json"),
    ("user", "./data/user.json"),
    ("review", "./data/review.json"),
]

# Define directory path for the photos
photo_dir_path = "./frontend/public/business_photo"

i = 0
for collection_name, file_path in collections_files:
    print(f"Importing {collection_name} collection...")
    collection = db[collection_name]
    requests = []

    with open(file_path, "r") as f:
        for jsonObj in f:
            document = json.loads(jsonObj)

            # If it's the business collection, handle the photo
            if collection_name == "business":
                # Define path for business photo
                photo_path = os.path.join(photo_dir_path, document["business_id"] + ".jpg")

                # If photo exists, store in the document
                if os.path.exists(photo_path):
                    document["business_pic"] =  document["business_id"] + ".jpg"
                else:
                    # Generate a random number between 1 and 10 to get a random photo
                    random_num = str(random.randint(1, 10))
                    random_photo_path = "business_" + random_num + ".jpg"
                    document["business_pic"] = random_photo_path
            
            # If it's the user collection, handle the photo
            if collection_name == "user":
                # Generate a random number between 1 and 10 to get a random photo
                random_num = str(random.randint(1, 10))
                random_photo_path = "user_" + random_num + ".jpg"
                document["profile_pic"] = random_photo_path

            requests.append(InsertOne(document))
            i += 1
            print(f"Inserted {i} {collection_name} documents", end="\r")

    result = collection.bulk_write(requests)

    i = 0

print("Importing complete!")
print("Creating mapping indexes...")
choice = input("Do you want to create mapping indexes? (y/n): ")

# Create dictionary mapping business_id and user_id to _id in the 'business' and 'user' collections
business_id_map = {doc["business_id"]: doc["_id"] for doc in db.business.find()}
user_id_map = {doc["user_id"]: doc["_id"] for doc in db.user.find()}

j = 0
# Iterate over the 'review' collection
for review in db.review.find():
    # If the business_id in the review exists in the business_id_map
    if review["business_id"] in business_id_map:
        # Update the review's business_id to the corresponding _id from 'business' collection
        db.review.update_one({"_id": review["_id"]}, {"$set": {"business_id": business_id_map[review["business_id"]]}})

    # If the user_id in the review exists in the user_id_map
    if review["user_id"] in user_id_map:
        # Update the review's user_id to the corresponding _id from 'user' collection
        db.review.update_one({"_id": review["_id"]}, {"$set": {"user_id": user_id_map[review["user_id"]]}})
    j += 1
    print(f"Updated {j} review documents", end="\r")

k = 0
# Iterate over the 'user' collection for history attribute
for user in db.user.find():
    if user.get("history", {}).get("business_id") in business_id_map:
        # Update the business_id inside history attribute to the corresponding _id from 'business' collection
        db.user.update_one(
            {"_id": user["_id"]}, {"$set": {"history.business_id": business_id_map[user["history"]["business_id"]]}}
        )
    k += 1
    print(f"Updated {k} user documents", end="\r")

# Remove 'business_id' from 'business' collection and 'user_id' from 'user' collection
db.business.update_many({}, {"$unset": {"business_id": ""}})
db.user.update_many({}, {"$unset": {"user_id": ""}})
db.review.update_many({}, {"$unset": {"review_id": ""}})

client.close()
