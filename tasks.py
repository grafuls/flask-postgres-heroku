from app import db, krapi
from celery import Celery
from datetime import timedelta
from decimal import Decimal
from models import Factors, History, Ledger
from sqlalchemy import desc

import os

celery = Celery(__name__)
celery.config_from_object(__name__)
celery.conf.update(BROKER_URL=os.environ['REDIS_URL'],
                   CELERY_RESULT_BACKEND=os.environ['REDIS_URL'])

def _get_latest(latest, pair):
    latest = [x.value for x in latest if x.currency == pair]
    return latest

@celery.task
def shakeThatMoneyMaker():
    XBT_PAIR = 'XXBTZUSD'
    ETH_PAIR = 'XETHZUSD'
    PAIR = ','.join([XBT_PAIR, ETH_PAIR])
    xbt_drop = False
    eth_drop = False

    latest = db.session.query(History).order_by(desc(History.id)).limit(6)
    xbt_latest = _get_latest(latest,  XBT_PAIR)
    xbt_average = sum(xbt_latest)/len(xbt_latest)
    eth_latest = _get_latest(latest, ETH_PAIR)
    eth_average = sum(eth_latest)/len(eth_latest)

    ticker = krapi.query_public('Ticker', {'pair': PAIR})
    xbt_price = ticker['result'][XBT_PAIR]['a'][0]
    eth_price = ticker['result'][ETH_PAIR]['a'][0]

    xbt_drop = Decimal(xbt_price) < xbt_average
    eth_drop = Decimal(eth_price) < eth_average

    balance = db.session.query(Ledger).order_by(desc(Ledger.id)).limit(1)[0]

    xbt = Money("xbt", 0, xbt_price)
    eth = Money("eth", 0, eth_price)

    if balance.usd > 0:
        split = balance.usd/2
        source = Money("usd", split, 1)
        _buy(source, xbt)
        _buy(source, eth)
        return

    if xbt_drop and not eth_drop:
        if balance.xbt > 0:
            source = Money("xbt", balance.xbt, xbt_price)
            _buy(source, eth)
        return

    if eth_drop and not xbt_drop:
        if balance.eth > 0:
            source = Money("eth", balance.eth, eth_price)
            _buy(source, xbt)
        return

    return


class Money():
    def __init__(self, currency, amount, usd_rate):
        self.currency = currency
        self.amount = Decimal(amount)
        self.usd_rate = Decimal(usd_rate)


def _buy(source, destination):
    balance = db.session.query(Ledger).order_by(desc(Ledger.id)).limit(1)[0]
    ledger = Ledger(rate=destination.usd_rate)
    conversion = convert(source, destination)
    factors_usd = 0
    factors_xbt = 0
    factors_eth = 0
    if source.currency in ("eth", "usd"):
        if destination.currency == "xbt":
            ledger.xbt = conversion + balance.xbt
            factors_xbt = conversion
            if source.currency == "usd":
                ledger.usd = balance.usd - source.amount
                factors_usd = - source.amount
                ledger.eth = balance.eth
            else:
                ledger.usd = balance.usd
                ledger.eth = balance.eth - source.amount
                factors_eth = - source.amount
    if source.currency in ("xbt", "usd"):
        if destination.currency == "eth":
            ledger.eth = conversion + balance.eth
            factors_eth = conversion
            if source.currency == "usd":
                ledger.usd = balance.usd - source.amount
                factors_usd = - source.amount
                ledger.xbt = balance.xbt
            else:
                ledger.usd = balance.usd
                ledger.xbt = balance.xbt - source.amount
                factors_xbt = - source.amount

    db.session.add(ledger)
    db.session.commit()
    db.session.refresh(ledger)

    factors = Factors(ledger.id, factors_usd, factors_xbt, factors_eth)
    db.session.add(factors)
    db.session.commit()


def convert(source, destination):
    pair = "ETHXBT"
    ticker = krapi.query_public('Ticker', {'pair': pair})
    rate = Decimal(ticker['result']['XETHXXBT']['a'][0])
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
        'task': 'tasks.shakeThatMoneyMaker',
        'schedule': timedelta(seconds=20),
    },
}
