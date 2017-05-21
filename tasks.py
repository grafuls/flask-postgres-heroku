from celery import Celery

import app
import os

celery = Celery(app.__name__)
celery.conf.update(BROKER_URL=os.environ['REDIS_URL'],
                   CELERY_RESULT_BACKEND=os.environ['REDIS_URL'])


@celery.task
def add(x, y):
    app.logger.info('Executing add function for %s*%s' % (x, y))
    return x + y
