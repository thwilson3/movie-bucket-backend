import os
import requests

from dotenv import load_dotenv
from flask_login import LoginManager, login_user
from sqlalchemy.exc import IntegrityError
from flask_migrate import Migrate
from helpers import (
    get_bucket,
    add_bucket,
    is_user_authorized,
    add_movie_to_bucket,
    delete_bucket,
    list_all_buckets,
    list_all_movies,
    create_response,
    create_bucket_link,
    verify_and_link_users,
)
from typing import Optional


from flask import Flask, request, jsonify

from models import db, connect_db, User

load_dotenv()

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
app.config["SQLALCHEMY_ECHO"] = False
app.config["API_KEY"] = os.environ["API_KEY"]
app.config["AUTH_KEY"] = os.environ["AUTH_KEY"]
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

connect_db(app)

migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)

AUTH_KEY = app.config["AUTH_KEY"]

HEADERS = {"accept": "application/json", "Authorization": f"Bearer {AUTH_KEY}"}

BASE_API_URL = "https://api.themoviedb.org/3/"


########################################################
###---------------------------------------SIGN-UP ROUTES


@login_manager.user_loader
def load_user(user_id: int) -> Optional[User]:
    user = User.query.get(int(user_id))
    if user:
        return user
    else:
        return None


@app.route("/signup", methods=["GET", "POST"])
def signup() -> jsonify:
    """Signs up a user, returns JSON w/message and success status"""

    data = request.get_json()

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    # Successful login
    try:
        user = User.signup(
            username=username,
            email=email,
            password=password,
        )

        db.session.commit()
        login_user(user)

        response = create_response("user signed up", True, "OK")

        return jsonify(response)

    # Failed login
    except IntegrityError:
        response = create_response("sign up failed", False, "Bad Request")

        return jsonify(response)


@app.route("/login", methods=["POST"])
def login() -> jsonify:
    """Authenticates user and logs them in.
    Returns JSON w/message and success status"""

    data = request.get_json()

    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()

    if user and user.authenticate(username=username, password=password):
        # Successful login
        login_user(user)
        response = create_response("logged in", True, "OK")
    else:
        # Failed login
        response = create_response("invalid credentials", False, "Unauthorized")

    return jsonify(response)


########################################################
###-------------------------------------API SEARCH ROUTE


@app.route("/api/search")
def list_search_results() -> jsonify:
    """Returns JSON list of search results"""

    query = request.args.get("query")

    url = f"{BASE_API_URL}search/movie"
    params = {"query": query}

    response = requests.get(url, params=params, headers=HEADERS)
    data = response.json()

    target_fields = ["title", "poster_path", "release_date", "overview"]

    filtered_results = [
        {field: result.get(field) for field in target_fields}
        for result in data["results"]
    ]

    return jsonify(filtered_results)


########################################################
###---------------------------------------BUCKET ROUTES


@app.route("/users/<int:user_id>/buckets", methods=["GET", "POST"])
def list_all_or_add_buckets(user_id: int) -> jsonify:
    """Returns JSON list of all buckets associated with a user"""

    user = User.query.get(user_id)

    if user is None:
        return jsonify(create_response("user not found", False, "Not Found"))

    # Serialize and return all buckets associated with user
    if request.method == "GET":
        serialized_buckets = list_all_buckets(user)

        return jsonify(serialized_buckets)

    # Create new bucket and associate it with user
    if request.method == "POST":
        data = request.get_json()

        response = add_bucket(user, data)

        return jsonify(response)


# TODO: consider separating routes into dedicated routes by method
@app.route("/users/buckets", methods=["GET", "DELETE"])
def get_or_delete_bucket() -> jsonify:
    """Get information in regards to single bucket or deletes that bucket"""

    user_id = request.args.get("user_id", type=int)
    bucket_id = request.args.get("bucket_id", type=int)

    bucket = get_bucket(bucket_id)

    if bucket is None:
        return jsonify(create_response("bucket not found", False, "Not Found"))

    if not is_user_authorized(bucket, user_id):
        return jsonify(create_response("user not authorized", False, "Unauthorized"))

    if request.method == "GET":
        users = [user.serialize() for user in bucket.users]
        response = {"bucket": bucket.serialize(), "authorized_users": users}

        return jsonify(response)

    elif request.method == "DELETE":
        response = delete_bucket(bucket)

        return jsonify(response)


@app.route("/users/buckets/movies", methods=["GET", "POST"])
def list_all_or_add_movie_to_bucket() -> jsonify:
    user_id = request.args.get("user_id", type=int)
    bucket_id = request.args.get("bucket_id", type=int)

    bucket = get_bucket(bucket_id)

    if bucket is None:
        return jsonify(create_response("bucket not found", False, "Not Found"))

    if not is_user_authorized(bucket, user_id):
        return jsonify(create_response("user not authorized", False, "Unauthorized"))

    if request.method == "GET":
        if not is_user_authorized(bucket, user_id):
            return jsonify(
                create_response("user not authorized", False, "Unauthorized")
            )
        serialized_movies = list_all_movies(bucket)
        return jsonify(serialized_movies)

    if request.method == "POST":
        if not is_user_authorized(bucket, user_id):
            return jsonify(
                create_response("user not authorized", False, "Unauthorized")
            )
        data = request.get_json()
        response = add_movie_to_bucket(bucket, data)
        return jsonify(response)


########################################################
###------------------------------------------LINK ROUTES


@app.get("/users/buckets/invite")
def invite_user_to_collaborate():
    """Generates invitation code for user to collaborate on a bucket"""

    user_id = request.args.get("user_id", type=int)
    bucket_id = request.args.get("bucket_id", type=int)

    bucket = get_bucket(bucket_id)

    if bucket is None:
        return jsonify(create_response("bucket not found", False, "Not Found"))

    if not is_user_authorized(bucket, user_id):
        return jsonify(create_response("user not authorized", False, "Unauthorized"))

    response = create_bucket_link(bucket_id)

    return jsonify(response)


@app.post("/users/buckets/link")
def link_additional_users_to_bucket():
    data = request.get_json()

    response = verify_and_link_users(data)

    if not response:
        return jsonify(create_response("invalid credentials", False, "Unauthorized"))

    return jsonify(response)
