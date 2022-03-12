from flask_sqlalchemy import SQLAlchemy
from app import app
from flask_login import UserMixin

db = SQLAlchemy(app)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String)
    email = db.Column(db.String, unique=True)
    password = db.Column(db.String)
    account_balance = db.Column(db.Integer, default=0)
    favorites = db.Column(db.String)
    creation_permit = db.Column(db.Boolean, default=False)
    notify_user = db.Column(db.Boolean, default=False)


class Collection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    creator = db.Column(db.Integer)
    title = db.Column(db.String)
    number_of_assets = db.Column(db.Integer)
    description = db.Column(db.String)
    logo_path = db.Column(db.String)
    banner_image = db.Column(db.String)
    creator_percentage = db.Column(db.Float)
    max_price = db.Column(db.Float)
    min_price = db.Column(db.Float)
    external_link = db.Column(db.String)


class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner = db.Column(db.Integer)
    creator = db.Column(db.Integer)
    asset_name = db.Column(db.String)
    status = db.Column(db.String, default=True)
    asking_price = db.Column(db.String)
    collection = db.Column(db.Integer)
    transaction_history = db.Column(db.String)
    asset_path = db.Column(db.String)
    blockchain = db.Column(db.String, default="Solana")
    contract_address = db.Column(db.String)
    wallet_address = db.Column(db.String)
    wallet_private = db.Column(db.String)
    token_id = db.Column(db.Integer)
    commission_fee = db.Column(db.Integer)


class Payout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    iban = db.Column(db.String)
    swift = db.Column(db.String)
    notes = db.Column(db.String)
    amount = db.Column(db.Float)


class CardInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_owner_fk = db.Column(db.Integer)
    card_number = db.Column(db.Integer)
    cvc = db.Column(db.Integer)
    card_owner_name = db.Column(db.String)
    valid_thru = db.Column(db.String)


class NFTCreatorApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    associated_user = db.Column(db.Integer)
    project_description = db.Column(db.String)
    discord_url = db.Column(db.String)
    website_url = db.Column(db.String)
    twitter_url = db.Column(db.String)


class NFTPriceOffer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    offered_asset = db.Column(db.Integer)
    offer_maker = db.Column(db.Integer)
    price = db.Column(db.Float)
