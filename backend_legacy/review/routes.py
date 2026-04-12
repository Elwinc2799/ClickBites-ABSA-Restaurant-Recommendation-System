from flask import Blueprint, Response, request
from database import Database
import json
from review.models import Review
from bson.objectid import ObjectId
from ai.generate_vector import generate_vector
from bson.objectid import ObjectId
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from scipy import stats


# Create a Flask blueprint for review related routes
review_bp = Blueprint("review", __name__)

# Get an instance of the database
db_review = Database.get_instance().get_db("review")
db_user = Database.get_instance().get_db("user")
db_business = Database.get_instance().get_db("business")


# Define normalization function
def normalize_vector(vector):
    return [(x + 1) / 2 * 4 + 1 for x in vector]


# Function to calculate aspect importance scores
def calc_importance_scores(group):
    aspect_importance_scores = []
    for i in range(5):
        # Calculate the weighted sum of the scores for each aspect
        aspect_values = np.array(group["normalized_review_vector"].tolist())[:, i]
        weighted_scores_sum = np.sum(group["stars"].values * aspect_values)

        # Calculate the square root of the sum of the squares of the ratings
        rating_sqrt = np.sqrt(np.sum(group["stars"].values ** 2))

        # Calculate the square root of the sum of the squares of the sentiment scores
        sentiment_sqrt = np.sqrt(np.sum(aspect_values**2))

        # Calculate the aspect importance score
        aspect_importance_scores.append(
            weighted_scores_sum / (rating_sqrt * sentiment_sqrt)
            if rating_sqrt * sentiment_sqrt != 0
            else 0  # Avoid division by zero
        )
    return aspect_importance_scores


# Function to calculate aspect need scores
def calc_need_scores(group):
    aspect_need_scores = []
    for i in range(5):
        aspect_values = np.array(group["normalized_review_vector"].tolist())[:, i]

        # Calculate the aspect need score for the aspect if it is mentioned in the review
        if np.any(aspect_values != 0):
            user_business_scores = []

            # For each business that the user has reviewed
            for business_id, business_group in group.groupby("business_id"):
                # Retrieve all reviews for the business that mention the aspect
                aspect_df = merged_df[
                    (merged_df["business_id"] == business_id)
                    & (merged_df["normalized_review_vector"].apply(lambda x: x[i] != 0))
                ]

                # Calculate the average of the aspect scores for the business
                Zi = aspect_df["normalized_review_vector"].apply(lambda x: x[i]).mean()

                # Calculate the average of the aspect scores for all the businesses that the user has reviewed
                user_score = business_group["normalized_review_vector"].apply(lambda x: x[i]).mean()

                # Calculate the aspect need score for the business
                user_business_scores.append((Zi - user_score + 1) / Zi)

            # Calculate the aspect need score for the aspect
            aspect_need_scores.append(np.mean(user_business_scores))
        else:
            # Calculate the aspect need score for the aspect if it is not mentioned in the review

            # Retrieve all scores for the aspect if it is mentioned in the review
            aspect_df = merged_df[merged_df["normalized_review_vector"].apply(lambda x: x[i] != 0)]

            # Calculate the average of the aspect scores for the aspect
            Z = aspect_df["normalized_review_vector"].apply(lambda x: x[i]).mean()

            # Calculate the aspect need score for the aspect
            aspect_need_scores.append(np.sum(0.1 / Z) / len(aspect_df))

    return aspect_need_scores


# Function to calculate aspect importance, need and preference scores for each user
def calculate_scores(user_df, review_df):
    # Merge the user and review dataframes based on user_id
    global merged_df
    merged_df = pd.merge(user_df, review_df, left_on="_id", right_on="user_id")

    # Normalize review vectors
    merged_df["normalized_review_vector"] = merged_df["vector_y"].apply(normalize_vector)

    def calc_scores(group):
        aspect_importance_scores = calc_importance_scores(group)
        # Print the aspect importance
        print("Aspect Importance Scores: ", aspect_importance_scores)

        aspect_need_scores = calc_need_scores(group)
        # Print the aspect need
        print("Aspect Need Scores: ", aspect_need_scores)

        preference_scores = np.array(aspect_importance_scores) * np.array(aspect_need_scores)

        # Print the preference_scores
        print("Preference Scores: ", preference_scores)

        return pd.Series({"vector": preference_scores.tolist()})

    user_scores = merged_df.groupby("user_id").apply(calc_scores)

    # return the vector of user_scores
    return user_scores


# Function to update user vector after a new review
def update_user_vector_after_new_review(review):
    # Retrieve all reviews for the user
    user_reviews = list(db_review.find({"user_id": ObjectId(review["user_id"])}))

    # Calculate the average stars
    average_stars = sum([user_review["stars"] for user_review in user_reviews]) / len(user_reviews)

    # Convert the list of reviews to a DataFrame
    review_df = pd.DataFrame(user_reviews)

    # Retrieve user data and convert it to a DataFrame
    user_data = list(db_user.find({"_id": ObjectId(review["user_id"])}))
    user_df = pd.DataFrame(user_data)

    print("Review Vector:", review["vector"])
    print("User Vector (before):", user_df["vector"].tolist()[0])

    # Calculate new preference scores
    updated_user_df = calculate_scores(user_df, review_df)

    # Update user's vector and average stars in MongoDB
    new_vector = updated_user_df.loc[review["user_id"], "vector"]
    vector_to_update = []

    # Update the user's vector based on the new review vector and the user's previous vector values
    for i in range(5):
        # If the review vector value is not 0, update the user's vector value
        if review["vector"][i] != 0:
            # Set the initial score to 0.5 if the user's vector value is 0, otherwise set it to the user's vector value
            initial_score = 0.5 if user_df["vector"].values[0][i] == 0 else user_df["vector"].values[0][i]

            # To prevent overflow of newly computed vector score, we will use the following formula to update the user's vector value

            # If the review vector value is positive, update the user's vector value by the formula (1 + (new_vector[i] * review["vector"][i])) * initial_score
            if abs(review["vector"][i]) > 0.5:
                vector_to_update.append((1 + (new_vector[i] * abs(review["vector"][i]))) * initial_score)
                print("New Vector:", i, vector_to_update)
            elif abs(review["vector"][i]) < 0.5:
                # If the review vector value is negative, update the user's vector value by the formula (1 - (new_vector[i] * review["vector"][i])) * initial_score
                vector_to_update.append((1 - (new_vector[i] * abs(review["vector"][i]))) * initial_score)
                print("New Vector:", i, vector_to_update)

        else:
            # If the review vector value is 0, do not update the user's vector value
            vector_to_update.append(user_df["vector"].values[0][i])
            print("New Vector:", i, vector_to_update)

    print("User Vector (after):", vector_to_update)

    # Normalize the vector to a standard normal distribution
    def normalize_to_distribution(lst, new_mean=0.5, new_std_dev=0.25):
        # Normalize to a standard normal distribution
        standardized_lst = stats.zscore(lst)

        # Shift mean to 0.5 and scale to desired range
        normalized_lst = new_std_dev * standardized_lst + new_mean

        # Clip values outside the desired range (0-1)
        normalized_lst = np.clip(normalized_lst, 0, 1)

        # Convert the numpy array to a list
        normalized_lst = normalized_lst.tolist()

        return normalized_lst

    vector_to_update = normalize_to_distribution(vector_to_update)

    db_user.update_one(
        {"_id": ObjectId(review["user_id"])},
        {
            "$set": {"vector": vector_to_update, "average_stars": average_stars},
            "$inc": {"review_count": 1},
        },
    )


# create a review for a business
@review_bp.route("/api/business/<string:business_id>", methods=["POST"])
def createReview(business_id):
    try:
        # get review object from response form
        review = Review().get()

        # convert the business id to review object
        review["business_id"] = ObjectId(business_id)

        # convert the review user id to an object id
        review["user_id"] = ObjectId(review["user_id"])

        # get the vector score for the review text
        vector_score = generate_vector(review["text"])

        # add the vector score to the review object
        review["vector"] = vector_score

        # post review object to database
        db_review.insert_one(review)

        # update user vector using enhanced algorithm from the research paper "Finding users preferences from large-scale online reviews for personalized recommendation"
        update_user_vector_after_new_review(review)

        # retrieve all reviews for the business
        business_reviews = list(db_review.find({"business_id": ObjectId(review["business_id"])}))

        # calculate the average stars and the business' aspect scores using average of all review scores
        average_stars = 0
        average_vector_score = [0] * 5
        for business_review in business_reviews:
            average_stars += int(business_review["stars"])
            for i in range(5):
                average_vector_score[i] += float(business_review["vector"][i])
        average_stars /= len(business_reviews)

        for i in range(5):
            average_vector_score[i] /= len(business_reviews)

        # print("average stars: ", average_stars)
        # print("average vector score: ", average_vector_score)

        # update the business object with the average stars and vector score and increment the review count
        db_business.update_one(
            {"_id": ObjectId(business_id)},
            {"$set": {"stars": average_stars, "vector": average_vector_score}, "$inc": {"review_count": 1}},
        )

        # Return a JSON message with a 200 OK status code and JSON mimetype
        return Response(
            response=json.dumps({"message": "The review data was successfully posted to the database"}),
            status=200,
            mimetype="application/json",
        )

    except Exception as e:
        # If an error occurred, return a JSON error message with a 500 Internal Server Error status code and JSON mimetype
        return Response(
            response=json.dumps(
                {
                    "message": "An error occurred while posting the review data to the database",
                }
            ),
            status=500,
            mimetype="application/json",
        )


# update a review for a business
@review_bp.route("/api/business/<string:business_id>/<string:review_id>", methods=["PUT"])
def updateReview(business_id, review_id):
    try:
        # get review object from response form
        updated_info = Review().get()

        # get the new vector score for the review text
        vector_score = generate_vector(updated_info["text"])

        # update review object in database with this list of data
        db_review.update_one(
            {"_id": ObjectId(review_id)},
            {
                "$set": {
                    "stars": updated_info["stars"],
                    "text": updated_info["text"],
                    "vector_score": vector_score,
                    "date": updated_info["date"],
                }
            },
        )

        # Return a JSON message with a 200 OK status code and JSON mimetype
        return Response(
            response=json.dumps(
                {
                    "message": "The review data was successfully updated in the database",
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
                    "message": "An error occurred while updating review data in the database",
                }
            ),
            status=500,
            mimetype="application/json",
        )


# delete a review for a business
@review_bp.route("/api/business/<string:business_id>/<string:review_id>", methods=["DELETE"])
def deleteReview(business_id, review_id):
    try:
        # delete review object from database
        db_review.delete_one({"_id": ObjectId(review_id)})

        # Return a JSON message with a 200 OK status code and JSON mimetype
        return Response(
            response=json.dumps({"message": "The review data was successfully deleted from the database"}),
            status=200,
            mimetype="application/json",
        )

    except Exception as e:
        # If an error occurred, return a JSON error message with a 500 Internal Server Error status code and JSON mimetype
        return Response(
            response=json.dumps(
                {
                    "message": "An error occurred while deleting the review data from the database",
                }
            ),
            status=500,
            mimetype="application/json",
        )
