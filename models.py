"""SQLAlchemy models for Movie Bucket."""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()


class Movie(db.Model):
    __tablename__ = "movies"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    title = db.Column(
        db.Text,
        nullable=False,
    )

    image = db.Column(
        db.Text,
        default=None,
    )

    release_date = db.Column(
        db.Text,
        default=None,
    )

    runtime = db.Column(
        db.Text,
        default=None,
    )

    genre = db.Column(
        db.Text,
        default=None,
    )

    bio = db.Column(
        db.Text,
        default=None,
    )

    is_watched = db.Column(
        db.Boolean,
        default=False,
    )

    def serialize(self):
        """Serializes all information tied to a movie"""

        data = {
            "id": self.id,
            "title": self.title,
            "is_watched": self.is_watched,
        }

        if self.image is not None:
            data["image"] = self.image

        if self.release_date is not None:
            data["release_date"] = self.release_date

        if self.runtime is not None:
            data["runtime"] = self.runtime

        if self.genre is not None:
            data["genre"] = self.genre

        if self.bio is not None:
            data["bio"] = self.bio

        return data


class User(db.Model, UserMixin):
    """User in the system."""

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    username = db.Column(
        db.String(16),
        nullable=False,
        unique=True,
    )

    email = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )

    password = db.Column(
        db.Text,
        nullable=False,
    )

    @classmethod
    def signup(cls, username, email, password):
        """Sign up user.

        Hashes password and adds user to system.
        """

        hashed_pwd = bcrypt.generate_password_hash(password).decode("UTF-8")

        user = User(
            username=username,
            email=email,
            password=hashed_pwd,
        )

        db.session.add(user)
        return user

    @classmethod
    def authenticate(cls, username, password):
        """Authenticates user."""

        user = cls.query.filter_by(username=username).first()

        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user

        return False

    def serialize(self):
        """Serializes all information tied to a user"""

        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
        }

        return data

    # establish relationship between user and buckets
    buckets = db.relationship("Bucket", secondary="user_buckets", backref="users")


class Bucket(db.Model):
    """Bucket to store movies"""

    __tablename__ = "buckets"

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
        default=None,
    )

    description = db.Column(
        db.Text,
        default=None,
    )

    def serialize(self):
        """Serializes all information tied to a bucket"""

        data = {
            "id": self.id,
            "bucket_name": self.bucket_name,
        }

        if self.genre is not None:
            data["genre"] = self.genre

        if self.description is not None:
            data["description"] = self.description

        return data

    # establish relationship between buckets and movies
    movies = db.relationship("Movie", secondary="buckets_movies", backref="buckets")


class User_Buckets(db.Model):
    """Join table between users and buckets."""

    __tablename__ = "user_buckets"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )

    bucket_id = db.Column(
        db.Integer,
        db.ForeignKey("buckets.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )


class Buckets_Movies(db.Model):
    """Join table between buckets and movies."""

    __tablename__ = "buckets_movies"

    bucket_id = db.Column(
        db.Integer,
        db.ForeignKey("buckets.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )

    movie_id = db.Column(
        db.Integer,
        db.ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )


def connect_db(app):
    """Connect db to app"""

    app.app_context().push()
    db.app = app
    db.init_app(app)
