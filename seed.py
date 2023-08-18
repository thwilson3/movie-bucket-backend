"""Seed database with sample data."""

from app import db
from models import Movie, User, Bucket, User_Buckets, Buckets_Movies

db.drop_all()
db.create_all()

# Create some movies
movie1 = Movie(title='Movie 1', release_date='2022-01-01', runtime='120 min', genre='Action', bio='Movie 1 description')
movie2 = Movie(title='Movie 2', release_date='2022-02-01', runtime='110 min', genre='Comedy', bio='Movie 2 description')
movie3 = Movie(title='Movie 3', release_date='2022-03-01', runtime='130 min', genre='Drama', bio='Movie 3 description')

# Add movies to the session
db.session.add_all([movie1, movie2, movie3])
db.session.commit()

# Create users
user1 = User.signup('user1', 'user1@example.com', 'password123')
user2 = User.signup('user2', 'user2@example.com', 'password456')

# Add users to the session
db.session.add_all([user1, user2])
db.session.commit()

# Create buckets
bucket1 = Bucket(bucket_name='Bucket 1', genre='Action', description='Bucket 1 description')
bucket2 = Bucket(bucket_name='Bucket 2', genre='Comedy', description='Bucket 2 description')

# Add buckets to the session
db.session.add_all([bucket1, bucket2])
db.session.commit()

# Create associations between users and buckets
user_bucket1 = User_Buckets(user_id=user1.id, bucket_id=bucket1.id)
user_bucket2 = User_Buckets(user_id=user1.id, bucket_id=bucket2.id)
user_bucket3 = User_Buckets(user_id=user2.id, bucket_id=bucket1.id)

# Add associations between users and buckets to the session
db.session.add_all([user_bucket1, user_bucket2, user_bucket3])
db.session.commit()

# Create associations between buckets and movies
bucket_movie1 = Buckets_Movies(bucket_id=bucket1.id, movie_id=movie1.id)
bucket_movie2 = Buckets_Movies(bucket_id=bucket1.id, movie_id=movie2.id)
bucket_movie3 = Buckets_Movies(bucket_id=bucket2.id, movie_id=movie3.id)

# Add associations between buckets and movies to the session
db.session.add_all([bucket_movie1, bucket_movie2, bucket_movie3])
db.session.commit()
