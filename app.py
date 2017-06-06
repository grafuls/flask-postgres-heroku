from decimal import Decimal
from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_heroku import Heroku

import krakenex
import os

app = Flask(__name__)
# SQLAlchemy config
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
heroku = Heroku(app)
db = SQLAlchemy(app)
api_key = os.environ['KRAKEN_API_KEY']
private_key = os.environ['KRAKEN_PRIVATE_KEY']
krapi = krakenex.API(api_key, private_key)

from models import Ledger, User, History  # noqa


# Set "homepage" to index.html
@app.route('/')
def index():
    XBT_PAIR = 'XXBTZUSD'
    ETH_PAIR = 'XETHZUSD'
    PAIR = ','.join([XBT_PAIR, ETH_PAIR])
    ticker = krapi.query_public('Ticker', {'pair': PAIR})
    xbt_price = ticker['result'][XBT_PAIR]['a'][0]
    eth_price = ticker['result'][ETH_PAIR]['a'][0]

    balance_query = krapi.query_private('Balance')
    balance = balance_query['result']
    balance_xbt = Decimal(balance['XXBT'])
    balance_eth = Decimal(balance['XETH'])
    balance_usd = Decimal(balance['ZUSD'])
    net_balance = (
        (balance_xbt * Decimal(xbt_price)) +
        (balance_eth * Decimal(eth_price)) +
        balance_usd
    )
    return render_template(
            'index.html',
            xbt_price=xbt_price,
            eth_price=eth_price,
            usd_balance=round(net_balance, 5),
            xbt_balance=round(balance_xbt, 5),
            eth_balance=round(balance_eth, 5),
            )


@app.route('/balance', methods=['GET'])
def balance():
    balance_query = krapi.query_private('Balance')
    balance = balance_query['result']
    balance_xbt = Decimal(balance['XXBT'])
    balance_eth = Decimal(balance['XETH'])
    return jsonify(
                xbt_balance=float(balance_xbt),
                eth_balance=float(balance_eth),
            )


@app.route('/price/<pairs>', methods=['GET'])
def price(pairs):
    ticker = krapi.query_public('Ticker', {'pair': pairs})
    prices = {}
    for pair, price in ticker['result'].items():
        maker_price = price['a'][0]
        h = History(pair, maker_price)
        db.session.add(h)
        db.session.commit()
        prices[pair] = maker_price
    return jsonify(pair=pairs, prices=prices)


if __name__ == '__main__':
    app.debug = True
    app.run()
