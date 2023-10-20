import os
import requests
import helpers

from dotenv import load_dotenv
from flask_login import LoginManager, login_user, logout_user
from sqlalchemy.exc import IntegrityError
from flask_migrate import Migrate
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    JWTManager,
)

from typing import Optional
from flask import Flask, request, jsonify
from celery import Celery
from models import db, connect_db, User
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
app.config["SQLALCHEMY_ECHO"] = False
app.config["API_KEY"] = os.environ["API_KEY"]
app.config["AUTH_KEY"] = os.environ["AUTH_KEY"]
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY")
app.config["ADMIN_TOKEN"] = os.environ["ADMIN_TOKEN"]
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]

jwt = JWTManager(app)

connect_db(app)

migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)

celery = Celery(
    'movie_bucket',
    broker='redis://localhost',
)

cors = CORS(app, origins="http://localhost:5173/*")

AUTH_KEY = app.config["AUTH_KEY"]

HEADERS = {"accept": "application/json", "Authorization": f"Bearer {AUTH_KEY}"}
BASE_API_URL = "https://api.themoviedb.org/3/"
TARGET_FIELDS_FOR_API = ["title", "poster_path", "release_date", "overview"]

MOVIE_FIELD_MAP = {
    "title": "title",
    "poster_path": "image",
    "release_date": "release_date",
    "overview": "bio",
}


########################################################
###---------------------------------------SIGN-UP ROUTES


@login_manager.user_loader
def load_user(user_id: int) -> Optional[User]:
    """flask login user loader"""

    user = User.query.get(int(user_id))
    if user:
        return user
    else:
        return None


@app.route("/signup", methods=["GET", "POST"])
def signup() -> jsonify:
    """Signs up a user, returns JSON w/message and success status"""

    data = request.get_json()

    username: str = data.get("username")
    email: str = data.get("email")
    password: str = data.get("password")

    # Successful signup
    try:
        user = User.signup(
            username=username,
            email=email,
            password=password,
        )

        db.session.commit()
        login_user(user)

        response = helpers.create_response(
            message="user signed up", success=True, status="OK"
        )

        return jsonify(response)

    # Failed signup
    except IntegrityError as err:
        error_message = err.orig.diag.message_detail
        response = helpers.create_response(
            message=f"{error_message}", success=False, status="Bad Request"
        )

        return jsonify(response)


@app.post("/login")
def login() -> jsonify:
    """Authenticates user and logs them in.
    Returns JSON w/message and success status"""

    data = request.get_json()

    username: str = data.get("username")
    password: str = data.get("password")

    user = User.query.filter_by(username=username).first()

    if user and user.authenticate(username=username, password=password):
        access_token = create_access_token(identity=user.id)
        login_user(user)
        response = helpers.create_response("logged in", True, "OK")
        response.update({"access_token": access_token})
    else:
        # Failed login
        response = helpers.create_response(
            message="invalid credentials", success=False, status="Unauthorized"
        )

    return jsonify(response)


@app.post("/logout")
@jwt_required()
def logout() -> jsonify:
    """Clears session and logs user out"""

    logout_user()

    return jsonify(
        helpers.create_response(message="logout successful", success=True, status="OK")
    )


########################################################
###-------------------------------------API SEARCH ROUTE


@app.route("/api/search/movies")
def list_search_results() -> jsonify:
    """Returns JSON list of search results"""

    query = request.args.get("query")

    url = f"{BASE_API_URL}search/movie"
    params = {"query": query}

    response = requests.get(url, params=params, headers=HEADERS)
    data = response.json()

    filtered_results = [
        {MOVIE_FIELD_MAP[field]: result.get(field) for field in TARGET_FIELDS_FOR_API}
        for result in data["results"]
    ]

    return jsonify(filtered_results)


########################################################
###---------------------------------------BUCKET ROUTES


@app.get("/users/buckets")
@jwt_required()
@helpers.performance_timer
def get_user_buckets_or_bucket_info() -> jsonify:
    """Returns JSON list of all buckets associated with the authenticated user
    or information about a single bucket if bucket_id is provided in query params"""

    # TODO: might be better to leave types off variable declaration
    user_id: int = get_jwt_identity()
    bucket_id: int = request.args.get("bucket_id", type=int)

    # If bucket_id is provided, retrieve information about a single bucket
    if bucket_id is not None:
        bucket = helpers.get_bucket(bucket_id)
        if bucket is None:
            return jsonify(
                helpers.create_response(
                    message="bucket not found", success=False, status="Not Found"
                )
            )

        if not helpers.is_user_authorized(bucket, user_id):
            return jsonify(
                helpers.create_response(
                    message="user not authorized", success=False, status="Unauthorized"
                )
            )

        users = helpers.get_auth_users(bucket)
        response = {"bucket": bucket.serialize(), "authorized_users": users}
        return jsonify(response)

    # Otherwise, retrieve all user buckets
    user = helpers.get_user(user_id=user_id)
    serialized_buckets = helpers.get_all_buckets(user)

    return jsonify(serialized_buckets)


@app.post("/users/buckets")
@jwt_required()
@helpers.performance_timer
def add_new_bucket() -> jsonify:
    """Adds a new bucket and returns JSON"""

    user_id: int = get_jwt_identity()

    user = helpers.get_user(user_id=user_id)
    data = request.get_json()
    response = helpers.add_bucket(user, data)

    return jsonify(response)


@app.delete("/users/buckets")
@jwt_required()
@helpers.performance_timer
def delete_single_bucket() -> jsonify:
    """Deletes specific bucket"""

    user_id: int = request.args.get("user_id", type=int)
    bucket_id: int = request.args.get("bucket_id", type=int)

    bucket = helpers.get_bucket(bucket_id)

    if bucket is None:
        return jsonify(
            helpers.create_response(
                message="bucket not found", success=False, status="Not Found"
            )
        )

    if not helpers.is_user_authorized(bucket, user_id):
        return jsonify(
            helpers.create_response(
                message="user not authorized", success=False, status="Unauthorized"
            )
        )

    response = helpers.delete_bucket(bucket)

    return jsonify(response)


@app.patch("/users/buckets")
@jwt_required()
@helpers.performance_timer
def update_bucket_info() -> jsonify:
    "Patches bucket resource"

    user_id: int = get_jwt_identity()
    bucket_id: int = request.args.get("bucket_id", type=int)
    data = request.get_json()

    bucket = helpers.get_bucket(bucket_id)

    if bucket is None:
        return jsonify(
            helpers.create_response(
                message="bucket not found", success=False, status="Not Found"
            )
        )

    if not helpers.is_user_authorized(bucket, user_id):
        return jsonify(
            helpers.create_response(
                message="user not authorized", success=False, status="Unauthorized"
            )
        )

    response = helpers.update_bucket(bucket, data)
    response.update({"bucket": bucket.serialize()})

    return jsonify(response)


@app.get("/users/buckets/movies")
@jwt_required()
@helpers.performance_timer
def get_all_movies_in_bucket() -> jsonify:
    """Lists all movies that exist inside of a bucket"""

    user_id: int = get_jwt_identity()
    bucket_id: int = request.args.get("bucket_id", type=int)

    bucket = helpers.get_bucket(bucket_id)

    if bucket is None:
        return jsonify(
            helpers.create_response(
                message="bucket not found", success=False, status="Not Found"
            )
        )

    if not helpers.is_user_authorized(bucket, user_id):
        return jsonify(
            helpers.create_response(
                message="user not authorized", success=False, status="Unauthorized"
            )
        )

    serialized_movies = helpers.get_all_movies(bucket)
    return jsonify(serialized_movies)


@app.post("/users/buckets/movies")
@jwt_required()
@helpers.performance_timer
def add_new_movie_to_bucket() -> jsonify:
    """Add a new movie to a bucket"""

    user_id: int = get_jwt_identity()
    bucket_id: int = request.args.get("bucket_id", type=int)

    bucket = helpers.get_bucket(bucket_id)

    if bucket is None:
        return jsonify(
            helpers.create_response(
                message="bucket not found", success=False, status="Not Found"
            )
        )

    if not helpers.is_user_authorized(bucket, user_id):
        return jsonify(
            helpers.create_response(
                message="user not authorized", success=False, status="Unauthorized"
            )
        )

    data = request.get_json()
    response = helpers.add_movie_to_bucket(bucket, data)
    return jsonify(response)


@app.patch("/users/buckets/movies")
@jwt_required()
@helpers.performance_timer
def update_movie_watch_status() -> jsonify:
    """Update movie is_watched status"""

    user_id: int = get_jwt_identity()
    bucket_id: int = request.args.get("bucket_id", type=int)
    movie_id: int = request.args.get("movie_id", type=int)

    bucket = helpers.get_bucket(bucket_id)
    movie = helpers.get_movie(movie_id)

    if bucket is None:
        return jsonify(
            helpers.create_response(
                message="bucket not found", success=False, status="Not Found"
            )
        )

    if movie is None:
        return jsonify(
            helpers.create_response(
                message="movie not found", success=False, status="Not Found"
            )
        )

    if not helpers.is_user_authorized(bucket, user_id):
        return jsonify(
            helpers.create_response(
                message="user not authorized", success=False, status="Unauthorized"
            )
        )

    response = helpers.toggle_movie_watch_status(movie)

    return jsonify(response)


########################################################
###------------------------------------------LINK ROUTES


@app.get("/users/buckets/invite")
@jwt_required()
@helpers.performance_timer
def invite_user_to_collaborate() -> jsonify:
    """Generates invitation code for user to collaborate on a bucket"""

    user_id: int = get_jwt_identity()
    bucket_id: int = request.args.get("bucket_id", type=int)

    bucket = helpers.get_bucket(bucket_id)

    if bucket is None:
        return jsonify(
            helpers.create_response(
                message="bucket not found", success=False, status="Not Found"
            )
        )

    if not helpers.is_user_authorized(bucket, user_id):
        return jsonify(
            helpers.create_response(
                message="user not authorized", success=False, status="Unauthorized"
            )
        )

    response = helpers.create_bucket_link(bucket_id)

    return jsonify(response)


@app.post("/users/buckets/link")
@jwt_required()
@helpers.performance_timer
def link_additional_users_to_bucket() -> jsonify:
    """Verifies invite code and adds user to auth users for bucket"""

    data = request.get_json()

    response = helpers.verify_and_link_users(data)

    if not response:
        return jsonify(
            helpers.create_response(
                message="invalid credentials", success=False, status="Unauthorized"
            )
        )

    return jsonify(response)


########################################################
###----------------------------------------PUBLIC ROUTES


# TODO: consider url params for public bucket id/easier for sharing
# TODO: could add usernames to anon users via cookies/session/local storage
@app.post("/public/buckets")
@helpers.performance_timer
def add_new_public_bucket() -> jsonify:
    """Adds a new bucket and returns JSON"""

    data = request.get_json()
    response = helpers.add_public_bucket(data)

    return jsonify(response)
