from celery.schedules import crontab
from movie_bucket.app import celery

#this needs to be imported for celery to run, despite the 'unused' error
from movie_bucket.tasks import clean_up_expired_links

celery.conf.beat_schedule = {
    'clean_up_expired_links': {
        'task': 'movie_bucket.tasks.clean_up_expired_links',
        'schedule': crontab(hour=0, minute=0),
    },
}

# crontab(hour=0, minute=0)
# crontab(minute='*/2')

# # If I decide to update where the backend results are stored, this is the conf
# celery.conf.update(
#     result_backend='redis://localhost:6379/0'
# )
