from flask import Flask, request


class User:
    def get(self):
        # get user data from response form
        user = request.get_json()
        return user
    