from decimal import Decimal
from flask import Flask, render_template, request, jsonify
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
krapi = krakenex.API()

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

    balance = db.session.query(Ledger).order_by(Ledger.id.desc()).first()
    usd_balance = (
        (Decimal(balance.xbt) * Decimal(xbt_price)) +
        (Decimal(balance.eth) * Decimal(eth_price))
    )
    return render_template(
            'index.html',
            xbt_price=xbt_price,
            eth_price=eth_price,
            usd_balance=usd_balance,
            xbt_balance=balance.xbt,
            eth_balance=balance.eth,
            )


# Save e-mail to database and send to success page
@app.route('/prereg', methods=['POST'])
def prereg():
    email = None
    if request.method == 'POST':
        email = request.form['email']
        if not db.session.query(User).filter(User.email == email).count():
            reg = User(email)
            db.session.add(reg)
            db.session.commit()
            return render_template('success.html')
    return render_template('index.html')


@app.route('/price/<pairs>', methods=['GET'])
def price(pairs):
    ticker = krapi.query_public('Ticker', {'pair': pairs})
    # price = ticker['result'][pair]['a'][0]
    prices = {}
    import ipdb;ipdb.set_trace()
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
