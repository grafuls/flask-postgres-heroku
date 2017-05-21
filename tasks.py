from celery import Celery
from datetime import timedelta

import app
import os

celery = Celery(app.__name__)
celery.conf.update(BROKER_URL=os.environ['REDIS_URL'],
                   CELERY_RESULT_BACKEND=os.environ['REDIS_URL'])


@celery.task
def add(x, y):
    print("%s+%s" % (x, y))
    return x + y

CELERYBEAT_SCHEDULE = {
    'every-second': {
        'task': 'example.say_hello',
        'schedule': timedelta(seconds=5),
    },
}
