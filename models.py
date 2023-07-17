"""SQLAlchemy models for Movie Bucket."""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Movie(db.Model):

    __tablename__ = 'movies'

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    title = db.Column(
        db.Text,
        nullable=False,
    )

    release_date = db.Column(
        db.Text,
    )

    runtime = db.Column(
        db.Text,
    )

    genre = db.Column(
        db.Text,
    )

    bio = db.Column(
        db.Text,
    )

class User(db.Model):
    """User in the system."""

    __tablename__ = 'users'

    username = db.Column(
        db.String(16),
        primary_key=True,
    )

    email = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )

class Bucket(db.Model):
    """Bucket to store movies"""

    __tablename__ = 'buckets'

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    bucket_name = db.Column(
        db.String(16),
        nullable=False,
    )

    genre = db.Column(
        db.Text,
    )

    description = db.Column(
        db.Text,
    )

class User_Buckets(db.Model):
    """Join table between users and buckets."""

    __tablename__ = 'user_buckets'

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.username', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
    )

    bucket_id = db.Column(
        db.Integer,
        db.ForeignKey('buckets.id', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
    )

class Buckets_Movies(db.Model):
    """Join table between buckets and movies."""

    __tablename__ = 'buckets_movies'

    bucket_id = db.Column(
        db.Integer,
        db.ForeignKey('buckets.id', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
    )

    movie_id = db.Column(
        db.Integer,
        db.ForeignKey('movies.id', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
    )

def connect_db(app):
    """Connect db to app"""

    app.app_context().push()
    db.app = app
    db.init_app(app)



# users ->> bucket
# bucket ->> users

# bucket ->> movies

###MOVIES:
# id
# title
# release date
# genre
# length
# bio

###USERS:
# username
# num_buckets
# bucket_list
# (ppl connected to?)

###BUCKETS:
# bucket_name
# movie_list
# FK* username
# FK* movie_id
# genre (optional)
# (ppl connected to?)