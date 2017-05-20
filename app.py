from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask.ext.sqlalchemy import SQLAlchemy

from flask.ext.heroku import Heroku

import krakenex
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
heroku = Heroku(app)
db = SQLAlchemy(app)
krapi = krakenex.API()


# Create our database model
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)

    def __init__(self, email):
        self.email = email

    def __repr__(self):
        return '<E-mail %r>' % self.email


class History(db.Model):
    __tablename__ = "history"
    id = db.Column(db.Integer, primary_key=True)
    currency = db.Column(db.String(8))
    value = db.Column(db.Numeric(10, 5))
    timestamp = db.Column(db.DateTime(), default=datetime.utcnow)

    def __init__(self, currency, value):
        self.currency = currency
        self.value = value


class Ledger(db.Model):
    __tablename__ = "ledger"
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(250))
    usd = db.Column(db.Numeric(10, 5))
    xbt = db.Column(db.Numeric(10, 5))
    eth = db.Column(db.Numeric(10, 5))
    rate = db.Column(db.Numeric(10, 5))
    commision = db.Column(db.Numeric(10, 5))
    direction = db.Column(db.String(8))

    def __init__(
            self,
            description=None,
            usd=0,
            xbt=0,
            eth=0,
            rate=0,
            direction=None):
        self.description = description
        self.usd = usd
        self.xbt = xbt
        self.eth = eth
        self.rate = rate
        self.commision = commision
        self.direction = direction


class Factors(db.Model):
    __tablename__ = "factors"
    id = db.Column(db.Integer, primary_key=True)
    usd = db.Column(db.Numeric(10, 5))
    xbt = db.Column(db.Numeric(10, 5))
    eth = db.Column(db.Numeric(10, 5))
    ledger_id = db.Column(db.Integer, ForeignKey("ledger.id"), nullable=False)

    def __init__(
            self,
            ledger_id,
            usd=0,
            xbt=0,
            eth=0
            ):
        self.ledger_id = ledger_id
        self.usd = usd
        self.xbt = xbt
        self.eth = eth


# Set "homepage" to index.html
@app.route('/')
def index():
    XBT_PAIR = 'XXBTZUSD'
    ETH_PAIR = 'XETHZUSD'
    PAIR = ','.join([XBT_PAIR, ETH_PAIR])
    ticker = krapi.query_public('Ticker', {'pair': PAIR})
    xbt_price = ticker['result'][XBT_PAIR]['a'][0]
    eth_price = ticker['result'][ETH_PAIR]['a'][0]
    return render_template(
            'index.html', xbt_price=xbt_price, eth_price=eth_price)


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


@app.route('/price/<pair>', methods=['GET'])
def price(pair):
    ticker = krapi.query_public('Ticker', {'pair': pair})
    # price = ticker['result'][pair]['a'][0]
    prices = {}
    for pair, prices in ticker['result'].items():
        maker_price = prices['a'][0]
        h = History(pair, maker_price)
        db.session.add(h)
        db.session.commit()
        prices[pair] = maker_price
    return jsonify(pair=pair, prices=prices)


if __name__ == '__main__':
    app.debug = True
    app.run()
