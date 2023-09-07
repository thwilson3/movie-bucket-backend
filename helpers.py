import string
import random
import time
import functools

from models import db, Bucket, User_Buckets, Movie, Buckets_Movies, User, BucketLink
from sqlalchemy.exc import IntegrityError
from typing import Dict, List
from datetime import datetime, timedelta

BUCKET_FIELDS = ["bucket_name", "genre", "description"]
USER_FIELDS = ["username", "email", "password"]


########################################################
###-------------------------------------------DB HELPERS


def create_bucket(bucket_name: str, genre: str, description: str) -> Bucket:
    """Create new Bucket instance and add to database"""

    try:
        new_bucket = Bucket(
            bucket_name=bucket_name, genre=genre, description=description
        )

        db.session.add(new_bucket)
        db.session.commit()

        return new_bucket

    except IntegrityError as err:
        db.session.rollback()

        error_message = err.orig.diag.message_detail

        raise err(error_message)


def update_bucket(bucket: Bucket, data: Dict):
    """Update bucket resource and commit to db"""

    for field in BUCKET_FIELDS:
        if field in data:
            setattr(bucket, field, data[field])

    try:
        db.session.commit()

    except IntegrityError as err:
        db.session.rollback()

        error_message = err.orig.diag.message_detail

        raise err(error_message)

    return create_response(message="bucket updated", success=True, status="OK")


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

    except IntegrityError as err:
        db.session.rollback()

        error_message = err.orig.diag.message_detail

        raise err(error_message)


def associate_user_with_bucket(user_id: int, bucket_id: int) -> bool:
    """Create association between user and newly made bucket"""

    try:
        user_bucket = User_Buckets(user_id=user_id, bucket_id=bucket_id)
        db.session.add(user_bucket)
        db.session.commit()
    except IntegrityError as err:
        db.session.rollback()

        error_message = err.orig.diag.message_detail

        raise err(error_message)

    return True


def associate_movie_with_bucket(bucket_id: int, movie_id: int) -> bool:
    """Create association between movie and bucket"""

    try:
        bucket_movie = Buckets_Movies(bucket_id=bucket_id, movie_id=movie_id)
        db.session.add(bucket_movie)
        db.session.commit()
    except IntegrityError as err:
        db.session.rollback()

        error_message = err.orig.diag.message_detail

        raise err(error_message)

    return True


def toggle_movie_watch_status(movie: Movie):
    """Toggles movie status"""
    try:
        movie.is_watched = not movie.is_watched
        db.session.add(movie)
        db.session.commit()

    except IntegrityError as err:
        db.session.rollback()

        error_message = err.orig.diag.message_detail

        raise err(error_message)

    response = create_response(
        message="movie patched successfully", success=True, status="OK"
    )
    response.update({"movie": movie.serialize()})

    return response


def create_bucket_link(bucket_id: int) -> Dict:
    """Creates instance of BucketLink and stores in db"""

    existing_links = BucketLink.query.filter_by(bucket_id=bucket_id).all()
    clean_up_links(existing_links)
    invite_code = generate_invite_code(5)
    expiration_date = datetime.now() + timedelta(minutes=5)

    try:
        new_link = BucketLink(
            bucket_id=bucket_id,
            invite_code=invite_code,
            expiration_date=expiration_date,
        )

        db.session.add(new_link)
        db.session.commit()

    except IntegrityError as err:
        db.session.rollback()

        error_message = err.orig.diag.message_detail

        raise err(error_message)

    response = create_response(
        message="invite code created", success=True, status="Accepted"
    )
    response.update(
        {
            "bucket_link": new_link.serialize(),
        }
    )
    return response


def verify_and_link_users(data: Dict[str, any]):
    """Verify code matches, associate new user with bucket, clean up link"""

    user_id: int = data.get("user_id")
    bucket_id: int = data.get("bucket_id")
    invite_code: str = data.get("invite_code")

    link = BucketLink.query.filter_by(bucket_id=bucket_id).first()

    if link and link.expiration_date > datetime.now():
        if invite_code == link.invite_code:
            associate_user_with_bucket(user_id=user_id, bucket_id=bucket_id)

            try:
                db.session.delete(link)
                db.session.commit()

            except IntegrityError as err:
                db.session.rollback()

                error_message = err.orig.diag.message_detail

                raise err(error_message)

            bucket = get_bucket(bucket_id=bucket_id)

            users = get_auth_users(bucket)

            response = create_response(
                message="user added to bucket", success=True, status="OK"
            )
            response.update({"bucket": bucket.serialize(), "authorized_users": users})

            return response

    return False


def delete_bucket(bucket: Bucket) -> Dict:
    """Delete a bucket and build a response"""

    try:
        db.session.delete(bucket)
        db.session.commit()

    except IntegrityError as err:
        db.session.rollback()

        error_message = err.orig.diag.message_detail

        raise err(error_message)

    response = create_response(message="bucket deleted", success=True, status="OK")

    return response


def clean_up_links(links: List) -> bool:
    for link in links:
        try:
            db.session.delete(link)
            db.session.rollback()

        except IntegrityError as err:
            db.session.rollback()

            error_message = err.orig.diag.message_detail

            raise err(error_message)

    return True


########################################################
###-----------------------------------MULTI-STEP HELPERS


def add_bucket(user, data):
    """Add/associate bucket to the user and create a response"""

    new_bucket = create_bucket(
        bucket_name=data.get("bucket_name"),
        genre=data.get("genre"),
        description=data.get("description"),
    )

    associate_user_with_bucket(user_id=user.id, bucket_id=new_bucket.id)

    users = get_auth_users(new_bucket)

    response = create_response(
        message="bucket accepted", success=True, status="Accepted"
    )
    response.update({"bucket": new_bucket.serialize(), "authorized_users": users})

    return response


def add_public_bucket(data):
    """Add public bucket and create a response"""

    new_bucket = create_bucket(
        bucket_name=data.get("bucket_name"),
        genre=data.get("genre"),
        description=data.get("description"),
    )

    response = create_response(
        message="bucket accepted", success=True, status="Accepted"
    )
    response.update({"bucket": new_bucket.serialize()})

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

    response = create_response(
        message="movie accepted", success=True, status="Accepted"
    )
    response.update(
        {
            "bucket": bucket.serialize(),
            "movie": new_movie.serialize(),
        }
    )
    return response


########################################################
###----------------------------------------QUERY HELPERS


def get_user(user_id: int):
    """Find user and return the instance"""

    return User.query.get(user_id)


def get_bucket(bucket_id: int):
    """Find bucket and return the instance"""

    return Bucket.query.get(bucket_id)


def get_movie(movie_id: int):
    """Find movie and return the instance"""

    return Movie.query.get(movie_id)


########################################################
###--------------------------------SERIALIZATION HELPERS


def get_all_movies(bucket: Bucket) -> List[Dict]:
    """Serializes all movies tied to a bucket"""

    serialized_movies = [movie.serialize() for movie in bucket.movies]
    return serialized_movies


def get_all_buckets(user: User) -> List[Dict]:
    """Serializes all buckets tied to a user"""

    serialized_buckets = [bucket.serialize() for bucket in user.buckets]
    return serialized_buckets


def get_auth_users(bucket: Bucket) -> List[Dict]:
    """Serializes all auth users tied to a bucket"""

    users = [user.serialize() for user in bucket.users]
    return users


########################################################
###----------------------------------------MISC HELPERS


def create_response(message: str, success: bool, status: str) -> Dict[str, str]:
    """Build a response for requests"""

    return {"message": message, "success": success, "status": status}


def is_user_authorized(bucket: Bucket, user_id: int) -> bool:
    """Verifies if user has authorization for a bucket"""

    user_ids = [user.id for user in bucket.users]
    return user_id in user_ids


def generate_invite_code(length: int) -> str:
    """Generate a code with only uppercase and digits based on given length"""

    characters = string.ascii_uppercase + string.digits
    return "".join(random.choice(characters) for _ in range(length))


# @celery.task
# def clean_up_expired_links():
#     """Automated function to clean up expired links"""

#     expired_links = BucketLink.query.filter(BucketLink.expiration_date < datetime.now())
#     link_amount = len(expired_links)
#     clean_up_links(links=expired_links)

#     print(
#         f"clean_up_expired_links ran at {datetime.now()}, {link_amount} links removed."
#     )

#     pass

# def test_celery_task():
#     result = clean_up_expired_links.apply_async()
#     task_result = result.get()
#     print(task_result)



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
