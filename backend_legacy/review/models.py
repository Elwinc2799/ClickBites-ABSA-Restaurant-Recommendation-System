from flask import Flask, request


class Review:
    def get(self):
        # get user data from response form
        review = request.get_json()
        return review
    
