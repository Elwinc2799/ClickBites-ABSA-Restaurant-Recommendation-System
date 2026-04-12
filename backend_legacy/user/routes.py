from flask import Blueprint, Response, request, jsonify
from database import Database
import json
from user.models import User
from bson.objectid import ObjectId
import jwt
from werkzeug.utils import secure_filename
import os
import uuid


# Create a Flask blueprint for user related routes
user_bp = Blueprint("user", __name__)

# Get an instance of the database
db_user = Database.get_instance().get_db("user")
db_review = Database.get_instance().get_db("review")
db_business = Database.get_instance().get_db("business")

# Define directory path for the photos
photo_dir_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "..", "..", "frontend", "public", "user_photo"
)


# signup
@user_bp.route("/api/signup", methods=["POST"])
def signUp():
    try:
        # Extract user details and image
        user = json.loads(request.form.get("user"))
        profile_pic = request.files.get("profile_pic")

        # TODO: Validate user input and create a new user in your database
        # ...

        # Handle the image file
        if profile_pic:
            # Generate a random UUID
            random_id = uuid.uuid4()

            filepath = os.path.join(photo_dir_path, str(random_id) + ".jpg")

            try:
                profile_pic.save(filepath)
                print(f"Successfully saved image at {filepath}")
            except Exception as e:
                print(f"Failed to save image: {str(e)}")

            # trim the file path to be relative to the frontend
            filepath = filepath.split("user_photo/")[1]

            user["profile_pic"] = filepath

        # initialize other necessary fields with 0/null
        user["review_count"] = 0
        user["average_stars"] = 0
        user["favourite"] = None
        user["history"] = None
        user["vector"] = [0] * 5

        # search for user in database
        document = db_user.find_one({"email": user.get("email")})

        # check if user exists
        if document is None:
            # post user object to database
            db_user.insert_one(user)

            # Return a JSON message with a 200 OK status code and JSON mimetype
            return Response(
                response=json.dumps({"message": "The user data was successfully posted to the database"}),
                status=200,
                mimetype="application/json",
            )
        else:
            return Response(
                response=json.dumps(
                    {
                        "message": "The user data was not posted to the database because it already exists",
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
                    "message": "An error occurred while posting user data to the database",
                }
            ),
            status=500,
            mimetype="application/json",
        )


# login
@user_bp.route("/api/login", methods=["POST"])
def login():
    try:
        # get user object from response form
        user = User().get()

        # search for user in database
        found = db_user.find_one(user)

        # check if user exists
        if found is None:
            # check if user email exists
            exists = db_user.find_one({"email": user.get("email")})
            if exists is None:
                return Response(
                    response=json.dumps(
                        {
                            "message": "The user data was not found in the database, please proceed to sign up",
                        }
                    ),
                    status=404,
                    mimetype="application/json",
                )
            else:
                return Response(
                    response=json.dumps(
                        {
                            "message": "Password incorrect",
                        }
                    ),
                    status=404,
                    mimetype="application/json",
                )
        else:
            token = jwt.encode({"sub": str(found["_id"])}, "super-secret-key", algorithm="HS256")

            # Return a JSON message with a 200 OK status code and JSON mimetype
            return Response(
                response=json.dumps(
                    {"message": "The user data was successfully validated with the database", "access_token": token}
                ),
                status=200,
                mimetype="application/json",
            )

    except Exception as e:
        # If an error occurred, return a JSON error message with a 500 Internal Server Error status code and JSON mimetype
        return Response(
            response=json.dumps(
                {
                    "message": "An error occurred while validating user data with the database",
                }
            ),
            status=500,
            mimetype="application/json",
        )


def decodeToken():
    # get the token from the Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header is None:
        return jsonify({"error": "Authorization header is missing"}), 401
    try:
        auth_token = auth_header.split(" ")[1]
    except IndexError:
        return jsonify({"error": "Invalid Authorization header format"}), 401

    # the secret key used to sign the token
    secret = "super-secret-key"

    try:
        # decode the token
        decoded = jwt.decode(auth_token, secret, algorithms=["HS256"])

        # the "sub" property contains the user ID
        user_id = decoded["sub"]

        # return the user ID as a JSON response
        return str(user_id)

    except jwt.ExpiredSignatureError:
        # handle the case where the token has expired
        return jsonify({"error": "Token has expired"}), 401

    except jwt.InvalidTokenError:
        # handle the case where the token is invalid
        return jsonify({"error": "Invalid token"}), 401


# retrieve user_id from token
@user_bp.route("/api/getUserId", methods=["GET"])
def getUserId():
    user_id = decodeToken()

    if isinstance(user_id, str):
        return jsonify({"userId": user_id})
    else:
        return user_id


# retrieve hasBusiness boolean flag
@user_bp.route("/api/getHasBusinessFlag", methods=["GET"])
def getHasBusinessFlag():
    # get user_id from token
    user_id = decodeToken()

    if isinstance(user_id, str):
        # search for user in database
        user = db_user.find_one({"_id": ObjectId(user_id)})

        # check if user exists
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
            # initialize hasBusiness flag if it does not exist
            if user.get("has_business") is None:
                user["has_business"] = False

            # Return a JSON message with a 200 OK status code and JSON mimetype
            return Response(
                response=json.dumps({"has_business": user["has_business"]}),
                status=200,
                mimetype="application/json",
            )
    else:
        return user_id


# retrieve user profile
@user_bp.route("/api/profile/<string:user_id>", methods=["GET"])
def retrieveProfile(user_id):
    try:
        # get user object from database
        document = db_user.find_one({"_id": ObjectId(user_id)})

        # check if user exists
        if document is None:
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
            # get all reviews for business
            reviews = list(db_review.find({"user_id": ObjectId(user_id)}))

            for review in reviews:
                # get business name
                business = db_business.find_one({"_id": ObjectId(review["business_id"])})
                if business is not None:
                    review["business_name"] = business["name"]
                    review["business_city"] = business["city"]

            document["reviews"] = reviews

            # Serialize the retrieved document to a JSON string
            user = json.dumps(document, default=str)

            # Return the JSON string with a 200 OK status code and JSON mimetype
            return Response(
                response=user,
                status=200,
                mimetype="application/json",
            )

    except Exception as e:
        # If an error occurred, return a JSON error message with a 500 Internal Server Error status code and JSON mimetype
        return Response(
            response=json.dumps(
                {
                    "message": "An error occurred while retrieving user data from the database",
                }
            ),
            status=500,
            mimetype="application/json",
        )


# update user information in profile page
@user_bp.route("/api/profile/<string:user_id>", methods=["PUT"])
def updateProfile(user_id):
    try:
        # get user object from response form
        updated_info = json.loads(request.form.get("user"))
        profile_pic = request.files.get("profile_pic")

        # Handle the image file
        if profile_pic:
            # Generate a random UUID
            random_id = uuid.uuid4()

            filepath = os.path.join(photo_dir_path, str(random_id) + ".jpg")

            try:
                profile_pic.save(filepath)
                print(f"Successfully saved image at {filepath}")
            except Exception as e:
                print(f"Failed to save image: {str(e)}")

            # trim the file path to be relative to the frontend
            filepath = filepath.split("user_photo/")[1]

            updated_info["profile_pic"] = filepath

        # search for user in database
        user = db_user.find_one({"_id": ObjectId(user_id)})

        # check if user exists
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
            # retrieve the image file
            try:
                if user["profile_pic"]:
                    filepath = os.path.join(photo_dir_path, user["profile_pic"])
                    os.remove(filepath)
                    print(f"Successfully removed image at {filepath}")
            except Exception as e:
                print(f"Image not found: {str(e)}")

            # update user object in database with this list of data
            db_user.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": updated_info},
            )

            # Return a JSON message with a 200 OK status code and JSON mimetype
            return Response(
                response=json.dumps(
                    {
                        "message": "The user data was successfully updated in the database",
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
                    "message": "An error occurred while updating user data in the database",
                }
            ),
            status=500,
            mimetype="application/json",
        )
