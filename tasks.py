from app import db, krapi
from celery import Celery
from datetime import timedelta
from decimal import Decimal
from models import History
from sqlalchemy import desc

import os

celery = Celery(__name__)
celery.config_from_object(__name__)
celery.conf.update(BROKER_URL=os.environ['REDIS_URL'],
                   CELERY_RESULT_BACKEND=os.environ['REDIS_URL'])

ETHXBT_PAIR = 'XETHXXBT'


@celery.task
def shakeThatMoneyMaker():
    XBT_PAIR = 'XXBTZUSD'
    ETH_PAIR = 'XETHZUSD'
    PAIR = ','.join([XBT_PAIR, ETH_PAIR, ETHXBT_PAIR])
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
    ethxbt_price = ticker['result'][ETHXBT_PAIR]['a'][0]

    xbt_drop = Decimal(xbt_price) < xbt_average
    eth_drop = Decimal(eth_price) < eth_average

    balance_query = krapi.query_private('Balance')
    balance = balance_query['result']

    orders_query = krapi.query_private('OpenOrders')
    orders = orders_query['result']

    balance_xbt = Decimal(balance['XXBT'])
    balance_eth = Decimal(balance['XETH'])

    if not orders['open']:
        if xbt_drop and not eth_drop:
            if balance_xbt > 0:
                print("Buying ETH with XBT")
                price = Decimal(ethxbt_price) - Decimal('0.00001')
                result = _order("buy", price, balance_xbt)
                print(result)
            return

        if eth_drop and not xbt_drop:
            if balance_eth > 0:
                print("Selling ETH for XBT")
                price = Decimal(ethxbt_price) + Decimal('0.00001')
                result = _order("sell", price, balance_eth)
                print(result)
            return

    return


def _get_latest(latest, pair):
    latest = [x.value for x in latest if x.currency == pair]
    return latest


def _order(type, price, volume):
    pair = ETHXBT_PAIR
    order = {
        'pair': pair,
        'type': type,
        'ordertype': 'limit',
        'price': price,
        'volume': volume
    }
    krapi.query_private("AddOrder", order)


CELERYBEAT_SCHEDULE = {
    'every-second': {
        'task': 'tasks.shakeThatMoneyMaker',
        'schedule': timedelta(seconds=20),
    },
}
