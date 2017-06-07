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
XBT_PAIR = 'XXBTZUSD'
ETH_PAIR = 'XETHZUSD'
PAIR = ','.join([XBT_PAIR, ETH_PAIR, ETHXBT_PAIR])
BUY = "buy"
SELL = "sell"


@celery.task
def shakeThatMoneyMaker():
    xbt_drop = False
    eth_drop = False

    try:
        latest = db.session.query(History).order_by(desc(History.id)).limit(6)
    except Exception as ex:
        print(ex)
        return

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

    xbt_latest = _get_latest(latest,  XBT_PAIR)
    xbt_average = sum(xbt_latest)/len(xbt_latest)
    eth_latest = _get_latest(latest, ETH_PAIR)
    eth_average = sum(eth_latest)/len(eth_latest)

    ticker = krapi.query_public('Ticker', {'pair': PAIR})
    xbt_price = Decimal(ticker['result'][XBT_PAIR]['a'][0])
    eth_price = Decimal(ticker['result'][ETH_PAIR]['a'][0])
    ethxbt_price = Decimal(ticker['result'][ETHXBT_PAIR]['a'][0])

    xbt_drop = xbt_price < xbt_average
    eth_drop = eth_price < eth_average
    xbt_mass_drop = xbt_price - 40 < xbt_average
    eth_mass_drop = eth_price - 40 < eth_average

    balance_xbt = Decimal(balance['XXBT'])
    balance_eth = Decimal(balance['XETH'])
    balance_usd = Decimal(balance['ZUSD'])
    buy_xbt = eth_drop and not xbt_drop
    buy_eth = xbt_drop and not eth_drop
    buy_usd = xbt_mass_drop and eth_mass_drop

    if not orders['open']:
        if buy_eth:
            if balance_xbt > 0:
                _execute_order(BUY, ETHXBT_PAIR, balance_xbt, ethxbt_price)
            if balance_usd > 0:
                _execute_order(BUY, ETH_PAIR, balance_usd, eth_price)
            return

        if buy_xbt:
            if balance_eth > 0:
                _execute_order(SELL, ETHXBT_PAIR, balance_eth, ethxbt_price)
            if balance_usd > 0:
                _execute_order(BUY, XBT_PAIR, balance_usd, xbt_price)
            return

        if buy_usd:
            if balance_xbt > 0:
                _execute_order(SELL, XBT_PAIR, balance_xbt, xbt_price)
            if balance_eth > 0:
                _execute_order(SELL, ETH_PAIR, balance_eth, eth_price)
            return

    return


def _get_latest(latest, pair):
    latest = [x.value for x in latest if x.currency == pair]
    return latest


def _execute_order(type_, pair, balance, price):
    source = pair[1:4]
    target = pair[-3:]
    ordertype = "limit"
    if type_ == "buy":
        volume = balance / (price - Decimal('0.00001'))
        action = "Buying"
        preposition = "with"
    else:
        action = "Selling"
        preposition = "for"
        if target == "USD":
            volume = balance
            ordertype = "market"
        else:
            volume = (balance * price) - Decimal('0.001')
    print(
        "%s %s:%.5f %s %s @%.5f" %
        (action, source, volume, preposition, target, price)
        )
    assert _order(pair, type_, price, volume, ordertype)


def _order(pair, type_, price, volume, ordertype):
    order = {
        'pair': pair,
        'type': type_,
        'ordertype': ordertype,
        'volume': volume,
        'expiretm': '+120',
    }
    if ordertype == "limit":
        order['price'] = price
    try:
        result = krapi.query_private("AddOrder", order)
        print(result)
    except Exception as ex:
        print(ex)
        return False
    return True


CELERYBEAT_SCHEDULE = {
    'every-second': {
        'task': 'tasks.shakeThatMoneyMaker',
        'schedule': timedelta(seconds=20),
    },
}
