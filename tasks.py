from app import db, krapi
from celery import Celery
from datetime import timedelta
from models import History, Ledger

import os

celery = Celery(__name__)
celery.config_from_object(__name__)
celery.conf.update(BROKER_URL=os.environ['REDIS_URL'],
                   CELERY_RESULT_BACKEND=os.environ['REDIS_URL'])


@celery.task
def add(x, y):
    print("%s+%s" % (x, y))
    return x + y


@celery.task
def shakeThatMoneyMaker():
    XBT_PAIR = 'XXBTZUSD'
    ETH_PAIR = 'XETHZUSD'
    PAIR = ','.join([XBT_PAIR, ETH_PAIR])
    xbt_drop = False
    eth_drop = False

    latest = db.session.query(History).order_by(History.id).limit(6)
    xbt_latest = [x.value for x in latest if x.currency == "XBTCZUSD"]
    xbt_average = sum(xbt_latest)/len(xbt_latest)
    eth_latest = [x.value for x in latest if x.currency == "XETHZUSD"]
    eth_average = sum(eth_latest)/len(eth_latest)

    ticker = krapi.query_public('Ticker', {'pair': PAIR})
    xbt_price = ticker['result'][XBT_PAIR]['a'][0]
    eth_price = ticker['result'][ETH_PAIR]['a'][0]

    xbt_drop = xbt_price < xbt_average
    eth_drop = eth_price < eth_average

    balance = db.session.query(Ledger).order_by(Ledger.id).limit(1)[0]

    xbt = Money("xbt", 0, xbt_price)
    eth = Money("eth", 0, eth_price)

    if balance.usd > 0:
        split = balance.usd/2
        source = Money("usd", split, 1)
        _buy(source, xbt, balance)
        _buy(source, eth, balance)
        return

    if xbt_drop and not eth_drop:
        if balance.xbt > 0:
            source = Money("xbt", balance.xbt, xbt_price)
            _buy(source, eth, balance)
        return

    if eth_drop and not xbt_drop:
        if balance.eth > 0:
            source = Money("eth", balance.eth, eth_price)
            _buy(source, xbt, balance)
        return

    return


class Money():
    def __init__(self, currency, amount, usd_rate):
        self.currency = currency
        self.amount = amount
        self.usd_rate = usd_rate


def _buy(source, destination, balance):
    ledger = Ledger(rate=destination.usd_rate)
    if source.currency in ("eth", "usd"):
        if destination.currency == "xbt":
            ledger.xbt == convert(source, destination) + balance.xbt
            if source.currency == "usd":
                ledger.usd = balance.usd - source.amount
                ledger.eth = balance.eth
            else:
                ledger.usd = balance.usd
                ledger.eth = balance.eth - source.amount
    if source.currency in ("xbt", "usd"):
        if destination.currency == "eth":
            ledger.eth == convert(source, destination) + balance.eth
            if source.currency == "usd":
                ledger.usd = balance.usd - source.amount
                ledger.eth = balance.eth
            else:
                ledger.usd = balance.usd
                ledger.xbt = balance.xbt - source.amount


def convert(source, destination):
    pair = "ETHXBT"
    ticker = krapi.query_public('Ticker', {'pair': pair})
    rate = ticker['result'][pair]['a'][0]
    total = 0
    if source.currency == "eth":
        total = source.amount * rate

    if source.currency == "xbt":
        total = source.amount / rate

    if source.currency == "usd":
        total = source.amount / destination.usd_rate

    return total


CELERYBEAT_SCHEDULE = {
    'every-second': {
        'task': 'tasks.add',
        'schedule': timedelta(seconds=5),
        'args': (1, 2),
    },
}
