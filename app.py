from flask import Flask, render_template, request, jsonify
from flask.ext.sqlalchemy import SQLAlchemy

from flask.ext.heroku import Heroku

import krakenex

app = Flask(__name__)
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


# Set "homepage" to index.html
@app.route('/')
def index():
    XBT_PAIR = 'XXBTZUSD'
    ETH_PAIR = 'XETHZUSD'
    xbt_ticker = krapi.query_public('Ticker', {'pair': XBT_PAIR})
    xbt_price = xbt_ticker['result'][XBT_PAIR]['a'][0]
    eth_ticker = krapi.query_public('Ticker', {'pair': ETH_PAIR})
    eth_price = eth_ticker['result'][ETH_PAIR]['a'][0]
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
    try:
        ticker = krapi.query_public('Ticker', {'pair': pair})
        print(pair)
        # price = ticker['result'][pair]['a'][0]
        prices = {}
        for price, value in ticker['result'].iteritems():
            prices[price] = value['a'][0]
        return jsonify(pair=pair, prices=prices)
    except Exception as ex:
        print(ex)


@app.route('/prices', methods=['GET'])
def prices():
    xbt_ticker = krapi.query_public('Ticker', {'pair': 'XXBTZUSD'})
    xbt_price = xbt_ticker['result']['XXBTZUSD']['a'][0]
    return jsonify(xbt_price=xbt_price)


if __name__ == '__main__':
    # app.debug = True
    app.run()
