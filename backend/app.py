# Description: This file is the entry point for the backend application. It
# registers the blueprints for the business, review, and user routes and
# starts the Flask application.

import os
from flask import Flask, session
from business.routes import business_bp
from review.routes import review_bp
from user.routes import user_bp
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_session import Session

app = Flask(__name__)


CORS(app, origins="http://localhost:3000", supports_credentials=True)

app.register_blueprint(business_bp)
app.register_blueprint(review_bp)
app.register_blueprint(user_bp)


if __name__ == "__main__":
    app.run(debug=True)
