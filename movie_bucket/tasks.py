from movie_bucket.app import celery
from helpers import clean_up_links
from models import BucketLink
from datetime import datetime

@celery.task()
def clean_up_expired_links():
    """Automated function to clean up expired links"""

    #TODO: link amount is always coming out to 2
    expired_links = BucketLink.query.filter(BucketLink.expiration_date < datetime.now())
    link_amount = expired_links.count()
    clean_up_links(links=expired_links)

    print(
        f"clean_up_expired_links ran at {datetime.now()}, {link_amount} links removed."
    )

    pass
