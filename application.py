import os

from flask import Flask, session, render_template, request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from hashlib import sha256

import requests, json


app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    """ Home Page """
    return render_template("home.html")

@app.route("/search", methods=["POST", "GET"])
def login_register():
    """ Login or Register """

    if request.method == "GET":
        return render_template("search.html", user=session["user_id"])

    username = request.form.get("username")
    password = request.form.get("password")
    pw_hash = sha256(password.encode()).hexdigest()

    if request.form["submit"] == "Login":

        # Check if username exists in DB
        if db.execute("SELECT username FROM users WHERE username = :username ", {"username":username}).rowcount == 1:
            true_pw_hash = db.execute("SELECT pw_hash FROM users WHERE username = :username ", {"username":username}).fetchall()[0][0]
            if(pw_hash == true_pw_hash):
                # If username and pw correct, login and redirect to search page
                session["user_id"] = db.execute("SELECT id FROM users WHERE username = :username ", {"username":username}).fetchall()[0][0]
                return render_template("search.html", username=username, user=session["user_id"])
            else:
                wrong_pw = "incorrect password for this username"
                return render_template("home.html", message=wrong_pw)
        else:
            user_not_found = "username not found"
            return render_template("home.html", message=user_not_found)

    elif request.form["submit"] == "Register":

        # Make sure username is not already in DB
        if db.execute("SELECT username FROM users WHERE username = :username ", {"username":username}).rowcount == 0:
            db.execute("INSERT INTO users (username, pw_hash) VALUES (:username, :pw_hash)", {"username": username, "pw_hash": pw_hash})
            db.commit()
            success_message = "registration successful, login below"
            return render_template("home.html", message=success_message)
        # If username already in DB, cannot register
        else:
            error_message = "username already exists, cannot register with this username"
            return render_template("home.html", message=error_message)

@app.route("/logged_out", methods=["POST"])
def logout():
    if(session["user_id"]):
        del session["user_id"]

    return render_template("home.html")

@app.route("/results", methods=["POST"])
def search():

    search_string = request.form.get("search")

    if search_string:
        if search_string.isalpha():
            search_string = search_string.upper()
        search_string = f"{search_string}%"
        locations = db.execute("SELECT zipcode, city, state, lat, long, population FROM locations WHERE zipcode LIKE :search_string OR city LIKE :search_string", {"search_string": search_string}).fetchall()
        return render_template("results.html", user=session["user_id"], locations=locations)
    else:
        empty_search_field = "Nothing entered, nothing to search"
        return render_template("search.html", message=empty_search_field, user=session["user_id"])

@app.route("/results/<string:city>/<lat>/<longg>")
def location(city, lat, longg):

    KEY = "8565f94778670d37d36772bcc5b2a904"
    get_request = f"https://api.darksky.net/forecast/{KEY}/{lat},{longg}"
    weather = requests.get(get_request).json()
    weather_now = weather["currently"]
    #print(json.dumps(weather["currently"], indent = 2))
    print(weather_now)
    return render_template("location.html", city=city, lat=lat, longg=longg)