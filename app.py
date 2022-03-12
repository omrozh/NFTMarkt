import flask
from flask_login import current_user, login_required, login_user, LoginManager, logout_user
from flask_bcrypt import Bcrypt
from random import randint
import stripe
import sys
import os
import inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from mint_nft import deploy_nft as nft_creator
from datetime import datetime

stripe.api_key = "sk_test_51HmZthKorNA5pIqqBJbZARQpNkzA023z58joe2L00ktZuSYBAwBW00q5" \
                 "xoPJ4yslocZxvRhC3nYyIWPqbEXgHWCG00O1NWmWQ5"

app = flask.Flask(__name__)

app.config["SECRET_KEY"] = "MakeMeABillionaire"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"

from models import User, Payout, Asset, Collection, db, CardInfo, NFTCreatorApplication, NFTPriceOffer

login_manager = LoginManager(app)
bcrypt = Bcrypt(app)

exchange_commission = 2


def charge_user(charge_data, amount):
    token = stripe.Token.create(
        card={
            "number": charge_data.card_number,
            "exp_month": int(charge_data.valid_thru.split("/")[0]),
            "exp_year": int(charge_data.valid_thru.split("/")[1]),
            "cvc": charge_data.cvc,
        },
    )

    charge = stripe.Charge.create(
        amount=int(float(amount)) * 100,
        currency="try",
        source=token.id,
        description="NFTMarkt varlık satın alımı",
    )

    return charge.get("paid")


@login_manager.user_loader
def userLoader(user_id):
    return User.query.get(user_id)


@app.route("/")
def index():
    return flask.render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    return flask.send_file("static/Markt.png")


@app.route("/file/<filename>")
def serveFile(filename):
    return flask.send_file(f"static/{filename}")


@app.route("/signup")
def signUp():
    return flask.redirect("/sign")


@app.route("/signin")
def signIn():
    return flask.redirect("/sign")


@app.route("/sign", methods=["POST", "GET"])
def sign():
    if current_user.is_authenticated:
        return flask.redirect("/home")
    if flask.request.method == "POST":
        values = flask.request.values

        if values["form-identifier"] == "signup":
            new_user = User(fullname=values['isim'], email=values["email"],
                            password=bcrypt.generate_password_hash(values["password"]))
            db.session.add(new_user)
            db.session.commit()
            return flask.redirect("/")
        elif values["form-identifier"] == "signin":
            try:
                user = User.query.filter_by(email=values["email"]).first()
                if bcrypt.check_password_hash(user.password, values["password"]):
                    login_user(user, remember=True)
            except AttributeError:
                return '''
                    <script>
                        alert("User does not exist")
                        window.location.reload()
                    </script>
                '''
            return flask.redirect("/home")

    return flask.render_template("signing.html")


@app.route("/create-collection", methods=["POST", "GET"])
@login_required
def createCollection():
    if not current_user.creation_permit:
        if flask.request.method == "POST":
            values = flask.request.values
            new_application = NFTCreatorApplication(associated_user=current_user.id,
                                                    project_description=values["project_description"],
                                                    discord_url=values["discord_url"],
                                                    website_url=values["website_url"],
                                                    twitter_url=values["twitter_url"])
            db.session.add(new_application)
            db.session.commit()

            return '''
                <script>
                    alert('Başvurunu aldık, takipte kal!')
                    document.location = '/profile'
                </script>
            '''
        return flask.render_template("apply_collection_permit.html")
    if flask.request.method == "POST":
        values = flask.request.values
        files = flask.request.files

        banner_file = files["banner-image"]

        file_name = str(randint(999999, 9999999)) + banner_file.name

        banner_file.save(f"static/{file_name}")

        new_collection = Collection(creator=current_user.id, number_of_assets=0,
                                    description=values["description"], banner_image=f"/file/{file_name}",
                                    title=values["title"], creator_percentage=int(values["creator_percentage"]),
                                    external_link=values["external_link"])

        db.session.add(new_collection)
        db.session.commit()

        return flask.redirect("/profile")

    return flask.render_template("create_collection.html")


@app.route("/create-asset/collection=<collection_id>", methods=["POST", "GET"])
@login_required
def create_asset(collection_id):
    current_collection = Collection.query.get(int(collection_id))
    if not current_collection.creator == current_user.id:
        return flask.abort(404)
    if flask.request.method == "POST":

        values = flask.request.values
        files = flask.request.files

        main_file = files["banner-image"]

        file_name = str(randint(999999, 9999999)) + main_file.name

        main_file.save(f"static/{file_name}")

        all_assets_in_collection = Asset.query.filter_by(collection=int(collection_id)).all()

        new_asset = Asset(owner=current_user.id, creator=current_user.id, asset_name=values["asset_name"],
                          asking_price=float(values["asking_price"]), collection=int(collection_id),
                          transaction_history=f"{datetime.today()}/{values['asking_price']}&&",
                          asset_path=f"/file/{file_name}", token_id=len(all_assets_in_collection),
                          commission_fee=current_collection.creator_percentage
                          )

        '''
        
        smart_contract, wallet_public, wallet_private = nft_creator.deployNFT(asset_path=file_name)

        new_asset.wallet_address = wallet_public
        new_asset.wallet_private = wallet_private
        new_asset.contract_address = smart_contract
        
        '''

        db.session.add(new_asset)

        all_assets_in_collection = Asset.query.filter_by(collection=int(collection_id)).all()

        max_price_in_collection = 0
        min_price_in_collection = 1000000000

        for i in all_assets_in_collection:
            if float(i.asking_price) > float(max_price_in_collection):
                max_price_in_collection = float(i.asking_price)
            if float(i.asking_price) < float(min_price_in_collection):
                min_price_in_collection = float(i.asking_price)

        current_collection.max_price = max_price_in_collection
        current_collection.min_price = min_price_in_collection

        db.session.commit()

        return flask.redirect("/profile")

    return flask.render_template("create_asset.html")


@app.route("/home")
@login_required
def discover():
    collections = Collection.query.all()
    notify_user = current_user.notify_user
    current_user.notify_user = False
    db.session.commit()
    return flask.render_template("discover.html", collections=collections, notify_user=notify_user)


@app.route("/profile")
@login_required
def profile():
    collections = Collection.query.filter_by(creator=current_user.id).all()
    assets = Asset.query.filter_by(owner=current_user.id).all()
    created_assets = Asset.query.filter_by(creator=current_user.id).all()

    return flask.render_template("profile.html", collections=collections, assets=assets, created_assets=created_assets,
                                 user=current_user)


@app.route("/view-collection/collection=<collection_id>")
@login_required
def view_collection(collection_id):
    assets = Asset.query.filter_by(collection=int(collection_id)).all()
    collection = Collection.query.get(int(collection_id))
    username = User.query.get(int(collection.creator)).fullname
    is_admin = current_user.id == collection.creator
    return flask.render_template("collection_view.html", assets=assets, collection=collection, creator=username,
                                 is_admin=is_admin)


@app.route("/view-asset/asset_id=<asset_id>", methods=["POST", "GET"])
@login_required
def view_asset(asset_id):
    asset = Asset.query.get(int(asset_id))

    if flask.request.method == "POST":
        if current_user.account_balance < float(flask.request.values["price_recommendation"]) or \
                float(flask.request.values["price_recommendation"]) < 0:
            return f'''
            <script>
                alert("Hesap bakiyeniz yetersiz")
                document.location = '/view-asset/asset_id={asset_id}'
            </script>
          '''
        new_offer = NFTPriceOffer(offered_asset=int(asset_id), offer_maker=current_user.id,
                                  price=float(flask.request.values["price_recommendation"]))
        User.query.get(int(asset.owner)).notify_user = True
        db.session.add(new_offer)
        db.session.commit()

    transactions = asset.transaction_history.split("&&")
    transactions.pop()

    dates = [str(i.split("/")[0].split(" ")[0]) for i in transactions]
    prices = [float(i.split("/")[1]) for i in transactions]

    similar = Asset.query.filter_by(collection=int(asset.collection)).all()

    is_not_for_sale = asset.status == "Not For Sale"
    is_owner = asset.owner == current_user.id

    offers = [{
        "offer_maker": User.query.get(int(i.offer_maker)).fullname,
        "price": i.price,
        "id": i.id
    } for i in NFTPriceOffer.query.filter_by(offered_asset=int(asset_id))]
    offers.reverse()

    return flask.render_template("asset_view.html", dates=dates, prices=prices, asset=asset, similar=similar,
                                 is_not_for_sale=is_not_for_sale, is_owner=is_owner, offers=offers)


@app.route("/checkout/asset_id=<asset_id>", methods=["POST", "GET"])
@login_required
def checkout(asset_id):
    asset = Asset.query.get(asset_id)
    if asset.status == "Not For Sale":
        return "Asset not for sale"

    user_cards = CardInfo.query.filter_by(card_owner_fk=current_user.id).all()
    user_card_numbers = [i.card_number for i in user_cards]

    if flask.request.method == "POST":
        values = flask.request.values
        if values["card-number"] not in user_card_numbers:
            card_info = CardInfo(card_owner_fk=current_user.id, card_number=values["card-number"],
                                 cvc=values["security-code"], card_owner_name=values["cardholder-name"],
                                 valid_thru=values["expiration-date"])

            db.session.add(card_info)
            db.session.commit()
        else:
            card_info = CardInfo(card_owner_fk=current_user.id, card_number=values["card-number"],
                                 cvc=values["security-code"], card_owner_name=values["cardholder-name"],
                                 valid_thru=values["expiration-date"])

        if charge_user(card_info, asset.asking_price):
            asset.transaction_history += f"{datetime.today()}/{asset.asking_price}&&"

            previous_owner = User.query.get(asset.owner)
            creator = User.query.get(asset.creator)

            previous_owner.account_balance += float(asset.asking_price) * float((100 - asset.commission_fee) / 100)
            creator.account_balance += float(asset.asking_price) * float(asset.commission_fee / 100)

            previous_owner.notify_user = True

            previous_owner.account_balance -= float(float(asset.asking_price) * float(exchange_commission / 100))

            asset.status = "Not For Sale"

            asset.owner = current_user.id

            db.session.commit()

            return flask.redirect(f"/view-asset/asset_id={asset_id}")

    return flask.render_template("checkout.html", asset=asset, saved_cards=user_cards, deposit=False)


@app.route("/sell/asset_id=<asset_id>", methods=["POST", "GET"])
@login_required
def sellAsset(asset_id):
    asset = Asset.query.get(asset_id)
    if not current_user.id == asset.owner:
        return flask.abort(404)

    if flask.request.method == "POST":
        asset.status = "For Sale"
        asset.asking_price = flask.request.values["asking_price"]

        current_collection = Collection.query.get(asset.collection)

        all_assets_in_collection = Asset.query.filter_by(collection=int(current_collection.id)).all()

        max_price_in_collection = 0
        min_price_in_collection = 1000000000

        for i in all_assets_in_collection:
            if float(i.asking_price) > float(max_price_in_collection):
                max_price_in_collection = float(i.asking_price)
            if float(i.asking_price) < float(min_price_in_collection):
                min_price_in_collection = float(i.asking_price)

        current_collection.max_price = max_price_in_collection
        current_collection.min_price = min_price_in_collection

        db.session.commit()

        return flask.redirect(f"/view-asset/asset_id={asset_id}")

    return flask.render_template("sell_asset.html", asset=asset)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return flask.redirect("/")


@app.route("/search", methods=["POST", "GET"])
@login_required
def searchCollections():
    pre_search_collections = Collection.query.all()
    if flask.request.method == "POST":
        collections = Collection.query.filter \
            (Collection.title.like('%' + flask.request.values["search_term"] + '%')).all()
        return flask.render_template("search.html", collections=collections)
    return flask.render_template("search.html", collections=pre_search_collections)


@app.route("/deposit", methods=["POST", "GET"])
def makeDeposit():
    user_cards = CardInfo.query.filter_by(card_owner_fk=current_user.id).all()
    user_card_numbers = [i.card_number for i in user_cards]

    if flask.request.method == "POST":
        values = flask.request.values

        if values["deposit-amount"] != values["amount-secure"]:
            return '''
                <script>
                    alert('Miktarlar Eşleşmiyor')
                    window.location = '/'
                </script>
            '''

        if values["card-number"] not in user_card_numbers:
            card_info = CardInfo(card_owner_fk=current_user.id, card_number=values["card-number"],
                                 cvc=values["security-code"], card_owner_name=values["cardholder-name"],
                                 valid_thru=values["expiration-date"])

            db.session.add(card_info)
            db.session.commit()

        else:
            card_info = CardInfo(card_owner_fk=current_user.id, card_number=values["card-number"],
                                 cvc=values["security-code"], card_owner_name=values["cardholder-name"],
                                 valid_thru=values["expiration-date"])

        if charge_user(card_info, float(values["deposit-amount"])):
            current_user.account_balance += float(values["deposit-amount"])
            db.session.commit()

        return flask.redirect("/profile")

    return flask.render_template("checkout.html", saved_cards=user_cards, deposit=True)


@app.route("/accept_offer/asset_id=<asset_id>/offer_id=<offer_id>")
@login_required
def acceptOffer(asset_id, offer_id):
    asset = Asset.query.get(int(asset_id))
    offer = NFTPriceOffer.query.get(int(offer_id))
    offer_maker = User.query.get(int(offer.offer_maker))
    asset_owner = User.query.get(int(asset.owner))
    creator = User.query.get(int(asset.creator))

    if asset.owner == current_user.id:
        if offer_maker.account_balance < offer.price:
            return flask.abort(500)

        offer_maker.account_balance -= offer.price

        asset_owner.account_balance += float(offer.price) * float((100 - asset.commission_fee) / 100)
        creator.account_balance += float(asset.asking_price) * float(asset.commission_fee / 100)

        asset_owner.account_balance -= float(offer.price * float(exchange_commission / 100))

        asset.owner = offer_maker.id

        asset.transaction_history += f"{datetime.today()}/{offer.price}&&"

        asset.asking_price = offer.price

        asset.status = "Not For Sale"

        current_collection = Collection.query.get(asset.collection)

        all_assets_in_collection = Asset.query.filter_by(collection=int(current_collection.id)).all()

        max_price_in_collection = 0
        min_price_in_collection = 1000000000

        for i in all_assets_in_collection:
            if float(i.asking_price) > float(max_price_in_collection):
                max_price_in_collection = float(i.asking_price)
            if float(i.asking_price) < float(min_price_in_collection):
                min_price_in_collection = float(i.asking_price)

        current_collection.max_price = max_price_in_collection
        current_collection.min_price = min_price_in_collection

        for i in NFTPriceOffer.query.filter_by(offered_asset=int(asset_id)):
            db.session.delete(i)

        db.session.commit()

        return flask.redirect(f"/view-asset/asset_id={asset_id}")
    else:
        return flask.redirect(f"/view-asset/asset_id={asset_id}")


@app.route("/terms")
def terms():
    return flask.render_template("terms.html")


@app.route("/withdraw-cash", methods=["POST", "GET"])
@login_required
def withdrawCash():
    if flask.request.method == "POST":
        values = flask.request.values
        if float(values["amount"]) > current_user.account_balance:
            return flask.render_template("withdraw_cash.html", amount_check=False)
        else:
            current_user.account_balance -= float(values["amount"])
            new_payout = Payout(amount=float(values["amount"]), notes=values["notes"], iban=values["iban"])
            db.session.add(new_payout)
            db.session.commit()
            return flask.redirect("/profile")
    return flask.render_template("withdraw_cash.html", amount_check=True)

# Add admin panel
