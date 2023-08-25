from models import db, Bucket, User_Buckets, Movie, Buckets_Movies
from sqlalchemy.exc import IntegrityError


def create_bucket(bucket_name, genre, description):
    """Create new Bucket instance and add to database"""

    try:
        new_bucket = Bucket(
            bucket_name=bucket_name, genre=genre, description=description
        )

        db.session.add(new_bucket)
        db.session.commit()

        return new_bucket

    except IntegrityError:
        raise Exception


def associate_user_with_bucket(user_id, bucket_id):
    """Create association between user and newly made bucket"""

    try:
        user_bucket = User_Buckets(user_id=user_id, bucket_id=bucket_id)
        db.session.add(user_bucket)
        db.session.commit()
    except IntegrityError:
        raise Exception

    return True


def create_movie(title, image, release_date, runtime, genre, bio):
    """Create new Movie instance and add to database"""

    try:
        new_movie = Movie(
            title=title,
            image=image,
            release_date=release_date,
            runtime=runtime,
            genre=genre,
            bio=bio
        )

        db.session.add(new_movie)
        db.session.commit()

        return new_movie

    except IntegrityError:
        raise Exception


def associate_movie_with_bucket(bucket_id, movie_id):
    """Create association between movie and bucket"""

    try:
        bucket_movie = Buckets_Movies(bucket_id=bucket_id, movie_id=movie_id)
        db.session.add(bucket_movie)
        db.session.commit()
    except IntegrityError:
        raise Exception

    return True
