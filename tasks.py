from celery import Celery

import app
import os

celery = Celery(app.name)
celery.conf.update(BROKER_URL=os.environ['REDIS_URL'],
                CELERY_RESULT_BACKEND=os.environ['REDIS_URL'])


@app.task
def add(x, y):
    return x + y
