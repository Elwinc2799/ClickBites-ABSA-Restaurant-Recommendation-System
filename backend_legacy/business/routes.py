from flask import Blueprint, Response, request, jsonify
from database import Database
import json
from bson.objectid import ObjectId
from business.models import Business
import jwt
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from werkzeug.utils import secure_filename
import os
from user.routes import decodeToken
from urllib.parse import unquote
import uuid

# Create a Flask blueprint for business related routes
business_bp = Blueprint("business", __name__)

# Get an instance of the database
db_business = Database.get_instance().get_db("business")
db_review = Database.get_instance().get_db("review")
db_user = Database.get_instance().get_db("user")

# Define directory path for the photos
photo_dir_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "..", "..", "frontend", "public", "business_photo"
)


# register a new business
@business_bp.route("/api/business", methods=["POST"])
def registerBusiness():
    try:
        # Extract business details and image
        business = json.loads(request.form.get("business"))
        business_pic = request.files.get("business_pic")

        user_id = decodeToken()

        if isinstance(user_id, str):
            # search for user in database
            user = db_user.find_one({"_id": ObjectId(user_id)})

            if user is None:
                return Response(
                    response=json.dumps(
                        {
                            "message": "The user data was not found in the database",
                        }
                    ),
                    status=404,
                    mimetype="application/json",
                )
            else:
                # Handle the image file
                if business_pic:
                    # Generate a random UUID
                    random_id = uuid.uuid4()

                    filepath = os.path.join(photo_dir_path, str(random_id) + ".jpg")

                    try:
                        business_pic.save(filepath)
                        print(f"Successfully saved image at {filepath}")
                    except Exception as e:
                        print(f"Failed to save image: {str(e)}")

                    # trim the file path to be relative to the frontend
                    filepath = filepath.split("business_photo/")[1]

                    business["business_pic"] = filepath

                # initialize other necessary fields with 0/null
                business["stars"] = 0
                business["review_count"] = 0
                business["view_count"] = 0
                business["vector"] = [0] * 5

                # search for business in database
                document = db_business.find_one({"name": business.get("name")})

                # check if business exists
                if document is None:
                    # post business object to database
                    db_business.insert_one(business)

                    # get the inserted business id
                    business_id = db_business.find_one({"name": business.get("name")})["_id"]

                    # Update user has_business flag to True
                    db_user.update_one(
                        {"_id": ObjectId(user_id)},
                        {"$set": {"has_business": True, "has_business_id": ObjectId(business_id)}},
                    )

                    # Return a JSON message with a 200 OK status code and JSON mimetype
                    return Response(
                        response=json.dumps({"message": "The business data was successfully posted to the database"}),
                        status=200,
                        mimetype="application/json",
                    )
                else:
                    return Response(
                        response=json.dumps(
                            {
                                "message": "The business data was not posted to the database because it already exists",
                            }
                        ),
                        status=404,
                        mimetype="application/json",
                    )
        else:
            return user_id

    except Exception as e:
        # If an error occurred, return a JSON error message with a 500 Internal Server Error status code and JSON mimetype
        return Response(
            response=json.dumps(
                {
                    "message": "An error occurred while posting business data to the database",
                }
            ),
            status=500,
            mimetype="application/json",
        )


# retrieve all businesses id
@business_bp.route("/api/businessid", methods=["GET"])
def getAllBusinessesId():
    try:
        # Get all documents from the business collection
        documents = list(db_business.find())

        # Extract the business id from each document
        businesses = [document["_id"] for document in documents]

        # Serialize the list of documents to a JSON string
        json_business = json.dumps(businesses, default=str)

        # Return the JSON string with a 200 OK status code and JSON mimetype
        return Response(
            response=json_business,
            status=200,
            mimetype="application/json",
        )

    except Exception as e:
        # If an error occurred, return a JSON error message with a 500 Internal Server Error status code and JSON mimetype
        return Response(
            response=json.dumps(
                {
                    "message": "An error occurred while fetching the business data",
                }
            ),
            status=500,
            mimetype="application/json",
        )



# retrieve a list of businesses based on search query
@business_bp.route("/api/results", methods=["GET"])
def getSearchResults():
    try:
        isLoggedIn = False
        # Get user ID from token
        user_id = decodeToken()

        if isinstance(user_id, str):
            isLoggedIn = True

        search_query = request.args.get("search_query")

        user_document = None
        user_vector = None

        if isLoggedIn:
            # Fetch user document by user_id
            user_document = db_user.find_one({"_id": ObjectId(user_id)})

            # Get user vector
            user_vector = np.array(user_document["vector"])

        def search_query_to_regex(search_query):
            return r"\b" + search_query + r"\b"

        # Get the search query regex
        search_query_regex = search_query_to_regex(search_query)

        # Perform a case-insensitive search for the search query in the business
        documents = list(
            db_business.find(
                {
                    "$or": [
                        {"categories": {"$regex": search_query_regex, "$options": "i"}},
                        {"name": {"$regex": search_query_regex, "$options": "i"}},
                        {"address": {"$regex": search_query_regex, "$options": "i"}},
                        {"city": {"$regex": search_query_regex, "$options": "i"}},
                        {"state": {"$regex": search_query_regex, "$options": "i"}},
                    ]
                }
            )
        )

        print(len(documents))

        if documents is not None:
            
            # check is user vector is not numpy array of 5 zeros
            if not np.array_equal(user_vector, np.zeros(5)) and isLoggedIn:
                user_vector = user_vector.reshape(1, -1)
                # Compute cosine similarity for each business and store it with the business document
                for document in documents:
                    if document["vector"] == None:
                        document["similarity"] = 0
                    else:
                        business_vector = np.array(document["vector"]).reshape(1, -1)
                        document["similarity"] = cosine_similarity(user_vector, business_vector)[0][0]

                # Sort documents by cosine similarity in descending order
                documents.sort(key=lambda x: x["similarity"], reverse=True)
            else:
                for document in documents:
                    document["similarity"] = 0
                # Sort documents by average stars in descending order
                documents.sort(key=lambda x: x["stars"], reverse=True)

            # Serialize the list of documents to a JSON string
            json_business = json.dumps(documents, default=str)

            # Return the JSON string with a 200 OK status code and JSON mimetype
            return Response(
                response=json_business,
                status=200,
                mimetype="application/json",
            )

    except Exception as e:
        # If an error occurred, return a JSON error message with a 500 Internal Server Error status code and JSON mimetype
        return Response(
            response=json.dumps(
                {
                    "message": "An error occurred while fetching the business data",
                }
            ),
            status=500,
            mimetype="application/json",
        )


# retrieve a business details
@business_bp.route("/api/business/<string:business_id>", methods=["GET"])
def getBusinessDetails(business_id):
    try:
        # get business object from database
        document = db_business.find_one({"_id": ObjectId(business_id)})

        # check if business exists
        if document is None:
            return Response(
                response=json.dumps(
                    {
                        "message": "The business data was not found in the database",
                    }
                ),
                status=404,
                mimetype="application/json",
            )
        else:
            # get all reviews for business
            reviews = list(db_review.find({"business_id": ObjectId(business_id)}))

            for review in reviews:
                # get user name
                user = db_user.find_one({"_id": ObjectId(review["user_id"])})

                if user is not None:
                    review["user_name"] = user["name"]
                else:
                    review["user_name"] = "Deleted User"
            
            document["reviews"] = reviews

            # Increment the view count
            db_business.update_one({"_id": ObjectId(business_id)}, {"$inc": {"view_count": 1}})

            # Serialize the retrieved document to a JSON string
            business = json.dumps(document, default=str)

            # Return the JSON string with a 200 OK status code and JSON mimetype
            return Response(
                response=business,
                status=200,
                mimetype="application/json",
            )

    except Exception as e:
        # If an error occurred, return a JSON error message with a 500 Internal Server Error status code and JSON mimetype
        return Response(
            response=json.dumps(
                {
                    "message": "An error occurred while retrieving business data from the database",
                }
            ),
            status=500,
            mimetype="application/json",
        )


# update business details
@business_bp.route("/api/business/<string:business_id>", methods=["PUT"])
def updateBusiness(business_id):
    try:
        # get user object from response form
        updated_info = json.loads(request.form.get("business"))
        business_pic = request.files.get("business_pic")

        # Handle the image file
        if business_pic:
            # Generate a random UUID
            random_id = uuid.uuid4()

            filepath = os.path.join(photo_dir_path, str(random_id) + ".jpg")

            try:
                business_pic.save(filepath)
                print(f"Successfully saved image at {filepath}")
            except Exception as e:
                print(f"Failed to save image: {str(e)}")

            # trim the file path to be relative to the frontend
            filepath = filepath.split("business_photo/")[1]

            updated_info["business_pic"] = filepath

        # search for business in database
        business = db_business.find_one({"_id": ObjectId(business_id)})

        # check if business exists
        if business is None:
            return Response(
                response=json.dumps(
                    {
                        "message": "The business data was not found in the database",
                    }
                ),
                status=404,
                mimetype="application/json",
            )
        else:
            # retrieve the image file
            if business_pic:
                filepath = os.path.join(photo_dir_path, business["business_pic"])

                os.remove(filepath)

            # update business object in database with this list of data
            db_business.update_one(
                {"_id": ObjectId(business_id)},
                {"$set": updated_info},
            )

            # Return a JSON message with a 200 OK status code and JSON mimetype
            return Response(
                response=json.dumps(
                    {
                        "message": "The business data was successfully updated in the database",
                    }
                ),
                status=200,
                mimetype="application/json",
            )

    except Exception as e:
        # If an error occurred, return a JSON error message with a 500 Internal Server Error status code and JSON mimetype
        return Response(
            response=json.dumps(
                {
                    "message": "An error occurred while updating business data in the database",
                }
            ),
            status=500,
            mimetype="application/json",
        )


# delete a business
@business_bp.route("/api/business/<string:business_id>", methods=["DELETE"])
def deleteReview(business_id):
    try:
        # delete business object from database
        db_business.delete_one({"_id": ObjectId(business_id)})

        # delete review object from database
        db_review.delete_many({"business_id": ObjectId(business_id)})

        # Return a JSON message with a 200 OK status code and JSON mimetype
        return Response(
            response=json.dumps({"message": "The business data was successfully deleted from the database"}),
            status=200,
            mimetype="application/json",
        )

    except Exception as e:
        # If an error occurred, return a JSON error message with a 500 Internal Server Error status code and JSON mimetype
        return Response(
            response=json.dumps(
                {
                    "message": "An error occurred while deleting the business data from the database",
                }
            ),
            status=500,
            mimetype="application/json",
        )


# retrieve a dashboard details
@business_bp.route("/api/dashboard", methods=["GET"])
def getDashboardDetails():
    try:
        # get user id from token
        user_id = decodeToken()

        # retrieve owned business id from user database
        user = db_user.find_one({"_id": ObjectId(user_id)})

        if user["has_business"]:
            # get business object from database
            document = db_business.find_one({"_id": ObjectId(user["has_business_id"])})

            # check if business exists
            if document is None:
                return Response(
                    response=json.dumps(
                        {
                            "message": "The business data was not found in the database",
                        }
                    ),
                    status=404,
                    mimetype="application/json",
                )
            else:
                # get all reviews for business
                reviews = list(db_review.find({"business_id": ObjectId(user["has_business_id"])}))

                for review in reviews:
                    # get user name
                    user = db_user.find_one({"_id": ObjectId(review["user_id"])})
                    review["user_name"] = user["name"]

                document["reviews"] = reviews

                # Serialize the retrieved document to a JSON string
                business = json.dumps(document, default=str)

                # Return the JSON string with a 200 OK status code and JSON mimetype
                return Response(
                    response=business,
                    status=200,
                    mimetype="application/json",
                )
        else:
            return Response(
                response=json.dumps(
                    {
                        "message": "The user does not have a business",
                    }
                ),
                status=404,
                mimetype="application/json",
            )

    except Exception as e:
        # If an error occurred, return a JSON error message with a 500 Internal Server Error status code and JSON mimetype
        return Response(
            response=json.dumps(
                {
                    "message": "An error occurred while retrieving business data from the database",
                }
            ),
            status=500,
            mimetype="application/json",
        )


# ************* Save retrieved data to a Business object ********************************
# from business.models import Business
# from business.models import Hours
#
# # Convert a list of dictionaries to a list of Business objects
# def json_to_business(json_list: List) -> List[Business]:
#     businesses = []
#     for item in json_list:
#         # Create a Hours object for the business
#         hours = Hours(
#             Monday=item["hours"].get("Monday", "") if item["hours"] else "",
#             Tuesday=item["hours"].get("Tuesday", "") if item["hours"] else "",
#             Wednesday=item["hours"].get("Wednesday", "") if item["hours"] else "",
#             Thursday=item["hours"].get("Thursday", "") if item["hours"] else "",
#             Friday=item["hours"].get("Friday", "") if item["hours"] else "",
#             Saturday=item["hours"].get("Saturday", "") if item["hours"] else "",
#             Sunday=item["hours"].get("Sunday", "") if item["hours"] else "",
#         )
#         # Create a Business object for the business
#         business = Business(
#             id=str(item["_id"]),
#             name=item["name"],
#             address=item["address"],
#             city=item["city"],
#             state=item["state"],
#             latitude=item["latitude"],
#             longitude=item["longitude"],
#             stars=item["stars"],
#             review_count=item["review_count"],
#             is_open=item["is_open"],
#             categories=item["categories"],
#             hours=hours,
#             description=item.get("description", ""),
#             view_count=item.get("view_count", 0),
#         )
#         businesses.append(business)
#     return businesses
#
# @business_bp.route("/business", methods=["GET"])
# def get_business():
#     try:
#         # Convert documents to a list of Business objects
#         business = json_to_business(documents)

#         # Serialize the list of Business objects to a JSON string
#         json_business = json_util.dumps([b.dict() for b in business])

#         Return a JSON message with a 200 OK status code and JSON mimetype

#         Return the JSON string with a 200 OK status code and JSON mimetype
#         return Response(
#             response=json_business,
#             status=200,
#             mimetype="application/json",
#         )
#     except Exception as e:
#         # If an error occurred, return a JSON error message with a 500 Internal Server Error status code and JSON mimetype
#         return Response(
#             response=json.dumps(
#                 {
#                     "message": "An error occurred while fetching the business data",
#                 }
#             ),
#             status=500,
#             mimetype="application/json",
#         )
# #######################################################################################
