import string
import random
import time
import functools

from models import db, Bucket, User_Buckets, Movie, Buckets_Movies, User, BucketLink
from sqlalchemy.exc import IntegrityError
from typing import Dict, List
from datetime import datetime, timedelta


def create_bucket(bucket_name: str, genre: str, description: str) -> Bucket:
    """Create new Bucket instance and add to database"""

    try:
        new_bucket = Bucket(
            bucket_name=bucket_name, genre=genre, description=description
        )

        db.session.add(new_bucket)
        db.session.commit()

        return new_bucket

        ##TODO: make these error messages more meaningful, example: ex.message/str(ex)
    except IntegrityError:
        raise Exception


def associate_user_with_bucket(user_id: int, bucket_id: int) -> bool:
    """Create association between user and newly made bucket"""

    try:
        user_bucket = User_Buckets(user_id=user_id, bucket_id=bucket_id)
        db.session.add(user_bucket)
        db.session.commit()
    except IntegrityError:
        raise Exception

    return True


def create_movie(
    title: str, image: str, release_date: str, runtime: str, genre: str, bio: str
) -> Movie:
    """Create new Movie instance and add to database"""

    try:
        new_movie = Movie(
            title=title,
            image=image,
            release_date=release_date,
            runtime=runtime,
            genre=genre,
            bio=bio,
        )

        db.session.add(new_movie)
        db.session.commit()

        return new_movie

    except IntegrityError:
        raise Exception


def associate_movie_with_bucket(bucket_id: int, movie_id: int) -> bool:
    """Create association between movie and bucket"""

    try:
        bucket_movie = Buckets_Movies(bucket_id=bucket_id, movie_id=movie_id)
        db.session.add(bucket_movie)
        db.session.commit()
    except IntegrityError:
        raise Exception

    return True


def create_response(message: str, success: bool, status: str) -> Dict[str, str]:
    """Build a response for requests"""

    return {"message": message, "success": success, "status": status}


def is_user_authorized(bucket: Bucket, user_id: int) -> bool:
    """Verifies if user has authorization for a bucket"""

    user_ids = [user.id for user in bucket.users]
    return user_id in user_ids


def get_bucket(bucket_id: int):
    """Find bucket and return the instance"""

    return Bucket.query.get(bucket_id)


def list_all_movies(bucket: Bucket) -> List[Dict]:
    """Serializes all movies tied to a bucket"""

    serialized_movies = [movie.serialize() for movie in bucket.movies]
    return serialized_movies


def list_all_buckets(user: User) -> List[Dict]:
    """Serializes all buckets tied to a user"""

    serialized_buckets = [bucket.serialize() for bucket in user.buckets]
    return serialized_buckets


def add_bucket(user, data):
    """Add/associate bucket to the user and create a response"""

    new_bucket = create_bucket(
        bucket_name=data.get("bucket_name"),
        genre=data.get("genre"),
        description=data.get("description"),
    )

    associate_user_with_bucket(user_id=user.id, bucket_id=new_bucket.id)

    users = [user.serialize() for user in new_bucket.users]

    response = create_response("bucket accepted", True, "Accepted")
    response.update({"bucket": new_bucket.serialize(), "authorized_users": users})

    return response


def add_movie_to_bucket(bucket: Bucket, data: Dict) -> Dict:
    """Add/associate movie to the bucket and create a response"""

    new_movie = create_movie(
        title=data.get("title"),
        image=data.get("image"),
        release_date=data.get("release_date"),
        runtime=data.get("runtime"),
        genre=data.get("genre"),
        bio=data.get("bio"),
    )

    associate_movie_with_bucket(bucket_id=bucket.id, movie_id=new_movie.id)

    response = create_response("movie accepted", True, "Accepted")
    response.update(
        {
            "bucket": bucket.serialize(),
            "movie": new_movie.serialize(),
        }
    )
    return response


def delete_bucket(bucket: Bucket) -> Dict:
    """Delete a bucket and build a response"""

    db.session.delete(bucket)
    db.session.commit()

    response = create_response("bucket deleted", True, "OK")

    return response


def generate_invite_code(length: int) -> str:
    """Generate a code with only uppercase and digits based on given length"""

    characters = string.ascii_uppercase + string.digits
    return "".join(random.choice(characters) for _ in range(length))


def create_bucket_link(bucket_id: int) -> Dict:
    """Creates instance of BucketLink and stores in db"""

    existing_links = BucketLink.query.filter_by(bucket_id=bucket_id).all()

    for link in existing_links:
        db.session.delete(link)

    invite_code = generate_invite_code(5)
    expiration_date = datetime.now() + timedelta(minutes=5)

    new_link = BucketLink(
        bucket_id=bucket_id, invite_code=invite_code, expiration_date=expiration_date
    )

    db.session.add(new_link)
    db.session.commit()

    response = create_response("invite code created", True, "Accepted")
    response.update(
        {
            "bucket_link": new_link.serialize(),
        }
    )
    return response


def verify_and_link_users(data):
    """Verify code matches, associate new user with bucket, clean up link"""

    user_id = data.get("user_id")
    bucket_id = data.get("bucket_id")
    invite_code = data.get("invite_code")

    link = BucketLink.query.filter_by(bucket_id=bucket_id).first()

    if link and link.expiration_date > datetime.now():
        if invite_code == link.invite_code:
            associate_user_with_bucket(user_id=user_id, bucket_id=bucket_id)

            db.session.delete(link)
            db.session.commit()

            bucket = get_bucket(bucket_id=bucket_id)

            users = [user.serialize() for user in bucket.users]

            response = create_response("user added to bucket", True, "OK")
            response.update({"bucket": bucket.serialize(), "authorized_users": users})

            return response

    return False


def performance_timer(func):
    """Decorator to help time function execution"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"{func.__name__} took {execution_time:.4f} seconds")
        return result
    return wrapper
