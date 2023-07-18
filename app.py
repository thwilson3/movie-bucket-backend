import os
import requests
from dotenv import load_dotenv

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

AUTH_KEY = app.config['AUTH_KEY']

HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {AUTH_KEY}"
}

BASE_API_URL = "https://api.themoviedb.org/3/"

########################################################

@app.route('/api/search')
def list_search_results():
    """Returns JSON list of search results"""

    query = request.args.get('query')

    url = f"{BASE_API_URL}search/movie"
    params = {"query": query}

    response = requests.get(url, params=params, headers=HEADERS)

    return jsonify(response.json())