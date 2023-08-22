import os
import requests
import json

from dotenv import load_dotenv
from flask_login import LoginManager, login_user
from sqlalchemy.exc import IntegrityError
from flask_migrate import Migrate


from flask import (
    Flask, request, jsonify
)

from models import (
    db, connect_db, User, Movie, Bucket
)

load_dotenv()

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_ECHO'] = False
app.config['API_KEY'] = os.environ['API_KEY']
app.config['AUTH_KEY'] = os.environ['AUTH_KEY']
app.secret_key = os.environ.get('FLASK_SECRET_KEY')

connect_db(app)

migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)

AUTH_KEY = app.config['AUTH_KEY']

HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {AUTH_KEY}"
}

BASE_API_URL = "https://api.themoviedb.org/3/"

########################################################

@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    if user:
        return user
    else:
        return None


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signs up a user, returns JSON w/message and success status"""

    data = request.get_json()

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # Successful login
    try:

        user = User.signup(
            username=username,
            email=email,
            password=password,
        )

        db.session.commit()
        login_user(user)

        response = {
            'message': 'Sign up successful',
            'success' : True
        }

        return jsonify(response)

    # Failed login
    except IntegrityError:

        response = {
            'message': 'Sign up failed',
            'success' : False
        }

        return jsonify(response)



@app.route('/login', methods=['POST'])
def login():
    """Authenticates user and logs them in.
    Returns JSON w/message and success status"""

    data = request.get_json()

    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user and user.authenticate(username=username, password=password):

        # Successful login
        login_user(user)
        response = {
            'message': 'Logged in successfully',
            'success': True
        }
    else:

        # Failed login
        response = {
            'message': 'Login failed. Please check your credentials.',
            'success': False
        }

    return jsonify(response)


@app.route('/api/search')
def list_search_results():
    """Returns JSON list of search results"""

    query = request.args.get('query')

    url = f"{BASE_API_URL}search/movie"
    params = {"query": query}

    response = requests.get(url, params=params, headers=HEADERS)

    return jsonify(response.json())


@app.route('/users/<int:user_id>/buckets', methods=['GET', 'POST'])
def list_users_buckets(user_id):
    """Returns JSON list of all buckets associated with a user"""

    user = User.query.get(user_id)

    if user is None:
        return jsonify({"message": "user not found"}), 404

    if request.method == 'GET':

        serialized_buckets = [bucket.serialize() for bucket in user.buckets]

        return jsonify(serialized_buckets)

    if request.method == 'POST':
        data = request.get_json()

        bucket_name = data.get('bucket_name')
        genre = data.get('genre')
        description = data.get('description')
        new_bucket = Bucket(
            bucket_name=bucket_name,
            genre=genre,
            description=description)

        db.session.add(new_bucket)
        db.session.commit()

        #TODO: reassess if this is the best response to give
        return jsonify({"message": "bucket created successfully"})

    #TODO: make this return something more meaningful
    return None


#TODO: verify this is working with both methods
@app.route('/users/<int:user_id>/buckets/<int:bucket_id>', methods=['GET', 'DELETE'])
def get_or_delete_bucket(user_id, bucket_id):

    user = User.query.get(user_id)

    if user is None:
        return jsonify({"message": "user not found"}), 404

    bucket = None
    for b in user.buckets:
        if b.id == bucket_id:
            bucket = b
            break

    if bucket is None:
        return jsonify({"message": "bucket not found"}), 404

    if request.method == 'GET':
        return jsonify(bucket.serialize())

    elif request.method == 'DELETE':
        db.session.delete(bucket)
        db.session.commit()

        return jsonify({"message": "bucket deleted successfully"}), 204