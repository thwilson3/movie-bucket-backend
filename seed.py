"""Seed database with sample data."""

from app import db
from models import Movie, User, Bucket, User_Buckets, Buckets_Movies

# Create some movies
movie1 = Movie(title='Movie 1', release_date='2022-01-01', runtime='120 min', genre='Action', bio='Movie 1 description')
movie2 = Movie(title='Movie 2', release_date='2022-02-01', runtime='110 min', genre='Comedy', bio='Movie 2 description')
movie3 = Movie(title='Movie 3', release_date='2022-03-01', runtime='130 min', genre='Drama', bio='Movie 3 description')

# Create some users
user1 = User(username='user1', email='user1@example.com')
user2 = User(username='user2', email='user2@example.com')

# Create some buckets
bucket1 = Bucket(bucket_name='Bucket 1', genre='Action', description='Bucket 1 description')
bucket2 = Bucket(bucket_name='Bucket 2', genre='Comedy', description='Bucket 2 description')

# Create associations between users and buckets
user_bucket1 = User_Buckets(user_id=user1.username, bucket_id=bucket1.id)
user_bucket2 = User_Buckets(user_id=user1.username, bucket_id=bucket2.id)
user_bucket3 = User_Buckets(user_id=user2.username, bucket_id=bucket1.id)

# Create associations between buckets and movies
bucket_movie1 = Buckets_Movies(bucket_id=bucket1.id, movie_id=movie1.id)
bucket_movie2 = Buckets_Movies(bucket_id=bucket1.id, movie_id=movie2.id)
bucket_movie3 = Buckets_Movies(bucket_id=bucket2.id, movie_id=movie3.id)

# Add objects to the session and commit changes
db.session.add_all([movie1, movie2, movie3, user1, user2, bucket1, bucket2,
                    user_bucket1, user_bucket2, user_bucket3, bucket_movie1,
                    bucket_movie2, bucket_movie3])
db.session.commit()
