import os
import requests

from dotenv import load_dotenv
from flask_login import LoginManager, login_user, logout_user, login_required
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
    performance_timer,
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

    # Successful signup
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

    # Failed signup
    except IntegrityError as err:
        error_message = err.orig.diag.message_detail
        response = create_response(f"{error_message}", False, "Bad Request")

        return jsonify(response)


@app.post("/login")
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

@app.post("/logout")
@login_required
def logout() -> jsonify:
    """Clears session and logs user out"""

    logout_user()

    return jsonify(create_response("logout successful", True, "OK"))


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


@app.get("/users/<int:user_id>/buckets")
@login_required
@performance_timer
def list_all_user_buckets(user_id: int) -> jsonify:
    """Returns JSON list of all buckets associated with a user"""

    user = User.query.get(user_id)

    if user is None:
        return jsonify(create_response("user not found", False, "Not Found"))

    serialized_buckets = list_all_buckets(user)

    return jsonify(serialized_buckets)


@app.post("/users/<int:user_id>/buckets")
@login_required
@performance_timer
def add_new_bucket(user_id: int) -> jsonify:
    """Adds a new bucket and returns JSON"""

    user = User.query.get(user_id)

    if user is None:
        return jsonify(create_response("user not found", False, "Not Found"))

    data = request.get_json()

    response = add_bucket(user, data)

    return jsonify(response)


@app.get("/users/buckets")
@login_required
@performance_timer
def get_bucket_info() -> jsonify:
    """Get information in regards to single bucket"""

    user_id = request.args.get("user_id", type=int)
    bucket_id = request.args.get("bucket_id", type=int)

    bucket = get_bucket(bucket_id)

    if bucket is None:
        return jsonify(create_response("bucket not found", False, "Not Found"))

    if not is_user_authorized(bucket, user_id):
        return jsonify(create_response("user not authorized", False, "Unauthorized"))

    users = [user.serialize() for user in bucket.users]
    response = {"bucket": bucket.serialize(), "authorized_users": users}

    return jsonify(response)


@app.delete("/users/buckets")
@login_required
@performance_timer
def delete_single_bucket() -> jsonify:
    """Deletes specific bucket"""

    user_id = request.args.get("user_id", type=int)
    bucket_id = request.args.get("bucket_id", type=int)

    bucket = get_bucket(bucket_id)

    if bucket is None:
        return jsonify(create_response("bucket not found", False, "Not Found"))

    if not is_user_authorized(bucket, user_id):
        return jsonify(create_response("user not authorized", False, "Unauthorized"))

    response = delete_bucket(bucket)

    return jsonify(response)


@app.get("/users/buckets/movies")
@login_required
@performance_timer
def list_all_movies_in_bucket() -> jsonify:
    """Lists all movies that exist inside of a bucket"""

    user_id = request.args.get("user_id", type=int)
    bucket_id = request.args.get("bucket_id", type=int)

    bucket = get_bucket(bucket_id)

    if bucket is None:
        return jsonify(create_response("bucket not found", False, "Not Found"))

    if not is_user_authorized(bucket, user_id):
        return jsonify(create_response("user not authorized", False, "Unauthorized"))

    serialized_movies = list_all_movies(bucket)
    return jsonify(serialized_movies)


@app.post("/users/buckets/movies")
@login_required
@performance_timer
def add_new_movie_to_bucket() -> jsonify:
    """Add a new movie to a bucket"""

    user_id = request.args.get("user_id", type=int)
    bucket_id = request.args.get("bucket_id", type=int)

    bucket = get_bucket(bucket_id)

    if bucket is None:
        return jsonify(create_response("bucket not found", False, "Not Found"))

    if not is_user_authorized(bucket, user_id):
        return jsonify(create_response("user not authorized", False, "Unauthorized"))

    data = request.get_json()
    response = add_movie_to_bucket(bucket, data)
    return jsonify(response)


########################################################
###------------------------------------------LINK ROUTES


@app.get("/users/buckets/invite")
@login_required
@performance_timer
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
@login_required
@performance_timer
def link_additional_users_to_bucket():
    data = request.get_json()

    response = verify_and_link_users(data)

    if not response:
        return jsonify(create_response("invalid credentials", False, "Unauthorized"))

    return jsonify(response)
