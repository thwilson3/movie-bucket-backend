import os
import requests

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

# @login_manager.user_loader
# def load_user(user_id):
#     user = User.query.get(int(user_id))
#     if user:
#         return user
#     else:
#         return None


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    print("yeeeeeeeeeeeeeeeeee")
    data = request.get_json()

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

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

    except IntegrityError:

        response = {
            'message': 'Sign up failed',
            'success' : False
        }

        return jsonify(response)



@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    username = data.get('username')

    user = User.query.filter_by(username=username).first()

    if user and user.is_authorized():
        # Successfully logged in
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

