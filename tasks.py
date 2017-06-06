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

    try:
        balance_query = krapi.query_private('Balance')
        print(balance_query)
        balance = balance_query['result']

        orders_query = krapi.query_private('OpenOrders')
        print(orders_query)
        orders = orders_query['result']
    except Exception as ex:
        print(ex)
        return

    balance_xbt = Decimal(balance['XXBT'])
    balance_eth = Decimal(balance['XETH'])

    if not orders['open']:
        if xbt_drop and not eth_drop:
            if balance_xbt > 0:
                price = Decimal(ethxbt_price) - Decimal('0.00001')
                volume = balance_xbt / price
                print("Buying ETH:%s with XBT @%s" % (volume, price))
                _order("buy", price, volume)
            return

        if eth_drop and not xbt_drop:
            if balance_eth > 0:
                price = Decimal(ethxbt_price) + Decimal('0.00001')
                volume = balance_eth * price
                print("Selling ETH:%s for XBT @%s" % (volume, price))
                _order("sell", price, volume)
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
        'volume': volume,
        'expiretm': '+60',
    }
    result = krapi.query_private("AddOrder", order)
    print(result)


CELERYBEAT_SCHEDULE = {
    'every-second': {
        'task': 'tasks.shakeThatMoneyMaker',
        'schedule': timedelta(seconds=20),
    },
}
