from app import db
from datetime import datetime


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
    timestamp = db.Column(db.DateTime(), default=datetime.utcnow)

    def __init__(
            self,
            description=None,
            usd=0,
            xbt=0,
            eth=0,
            rate=0,
            commision=0,
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
    ledger_id = db.Column(
        db.Integer,
        nullable=False
        )

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

db.create_all()
db.session.commit()
