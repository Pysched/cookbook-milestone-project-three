import os, json, math, html
import re
from flask import Flask, render_template, redirect, request, session, g, url_for, flash, Markup
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date
from flask_uploads import UploadSet, configure_uploads, IMAGES

# Instance of Flask
app = Flask(__name__)

# Config for storing uploaded images
images = UploadSet('images', IMAGES)
app.config["UPLOADED_IMAGES_DEST"] = "static/img"
configure_uploads(app, images)

# Config Flask app and connect to database
app.config["MONGO_DBNAME"] = 'onlineCookbook'
app.config["MONGO_URI"] = os.getenv('MONGO_URI')
# Secret key to enable user sessions for login and flash messages - generates random string
app.secret_key = os.urandom(24)

# Instance of PyMongo
mongo = PyMongo(app)

# DB collection variables
recipes_coll = mongo.db.recipes
rating_coll = mongo.db.rating
categories_coll = mongo.db.categories
serves_coll = mongo.db.serves
time_coll = mongo.db.time
types_coll = mongo.db.types
occasions_coll = mongo.db.occasions
cuisines_coll = mongo.db.cuisines
main_ing_coll = mongo.db.main_ing
users_coll = mongo.db.userLogin

# Functions for drop down menus (called multiple times in other functions)
def rating_dropdown():
    '''
    Drop down menu for rating values
    Accesses rating array within the rating database
    '''
    return [
        r for rating in rating_coll.find()
        for r in rating.get("rating")]

def time_dropdown():
    '''
    Drop down menu for time values (prep time and cook time)
    Accesses time array within the time database
    '''
    return [
        t for time in time_coll.find()
        for t in time.get("time")]

def serves_dropdown():
    '''
    Drop down menu for serves values (how many people the recipe serves)
    Accesses serves array within the serves database
    '''
    return [
        s for serves in serves_coll.find()
        for s in serves.get("serves")]

# def types_dropdown():
#     '''
#     Drop down menu for types values
#     Accesses types array within the types database
#     '''
#     return [
#         t for types in types_coll.find()
#         for t in types.get("types")]

# def occasions_dropdown():
#     '''
#     Drop down menu for occasions values
#     Accesses occasions array within the occasions database
#     '''
#     return [
#         o for occ in occasions_coll.find()
#         for o in occ.get("occasions")]

# def cuisines_dropdown():
#     '''
#     Drop down menu for cusines values
#     Accesses cusines array within the cusines database
#     '''
#     return [
#         c for cuisine in cuisines_coll.find()
#         for c in cuisine.get("cuisines")]

# def main_ing_dropdown():
#     '''
#     Drop down menu for main_ing values
#     Accesses main_ing array within the main_ing database
#     '''
#     return [
#         m for main in main_ing_coll.find()
#         for m in main.get("main_ing")]

def categories_dropdown(key, val):
    '''
    Drop down menu for categories values (type, occasion, cuisine & main_ing
    These are arrays that are nested within the categories object in the database
    The function uses the key, val parameters to access the relevant nested array
    '''
    for c in categories_coll.find():
        return c[key][val]
    
# Other global variables (called in multiple functions)
rating_list = rating_dropdown()
time_list = time_dropdown()
serves_list = serves_dropdown()
types_list = categories_dropdown('categories', 'type')
occasions_list = categories_dropdown('categories', 'occasion')
cuisines_list = categories_dropdown('categories', 'cuisine')
main_ing_list = categories_dropdown('categories', 'main_ing')

# Other helper functions (called multiple times in other functions)

# Route to index.html
@app.route('/')
def index():
    return render_template("index.html")

'''
USER LOGIN AND LOGOUT FUNCTIONALITY
'''

@app.route('/login_register')
def login_register():
    return render_template("login_register.html")
    
@app.route('/login', methods=["GET", "POST"])
def login():
    '''
    Login
    Checks that the user exists, and that user's password matches the
    hased password in the database
    '''
    if request.method == "POST":
        
        username = request.form.get('username').lower()
        password = request.form.get("password")
        existing_user = users_coll.find_one({"username": username})
        
        # Check if username exists and user's password matches the hashed password
        if existing_user and check_password_hash(existing_user["password"], password):
            flash(Markup("Welcome back " + username + ", you're now logged in!"))
            session['user'] = username
            return redirect(url_for('index'))
        # If either the username or password don't match, generic flash message is displayed
        else:
            flash(Markup("It appears those details don't match what we have, please try again."))
            return redirect(url_for('login'))
            
    return render_template("login_register.html")

@app.route('/register', methods=["GET", "POST"])
def register():
    '''
    Create new user/register new account
    Checks that the user doesn't already exist, and that length of username
    and password is between 6-15 characters
    Uses generate_password_hash to hash user's password in the database
    '''
    if request.method == "POST":
        
        new_username = request.form.get('new_username').lower()
        new_password = request.form.get("new_password")
        
        # Check username and password are alphanumeric
        for letter in new_username:
            if not letter.isalnum():
                flash(Markup("Usernames must be alphanumeric only. Please try another one."))
                return redirect(url_for('register'))
        for letter in new_password:
            if not letter.isalnum():
                flash(Markup("Passwords must be alphanumeric only. Please try another one."))
                return redirect(url_for('register'))
        
        # Check username and password are between 6-15 characters
        if len(new_username) < 5 or len(new_username) > 15:
            flash(Markup("Usernames must be between 5 and 15 characters. Please try again."))
            return redirect(url_for('register'))
        if len(new_password) < 5 or len(new_password) > 15:
            flash(Markup("Passwords must be between 5 and 15 characters. Please try again."))
            return redirect(url_for('register'))
        
        # Check if username already exists
        existing_user = users_coll.find_one({"username": new_username})
        if existing_user:
            flash(Markup("Sorry, " + new_username + " is already taken! Please choose another one!"))
            return redirect(url_for('register'))
        
        # If all checks pass, add user to the database and hash the password
        users_coll.insert_one({
            "username": new_username,
            "password": generate_password_hash(new_password)
        })
        session['user'] = new_username
        flash(Markup("Welcome " + new_username + ", you're now logged in!"))
        return redirect(url_for('index'))
    
    return render_template("login_register.html")

@app.route('/logout')
def logout():
    '''
    Remove the session cookie and end the user session
    '''
    session.pop('user', None)
    flash(Markup("You were successfully logged out"))
    return redirect(url_for('index'))

@app.before_request
def before_request():
    '''
    Checks if the user is logged in before each request
    '''
    g.user = None
    if 'user' in session:
        g.user = session['user']

'''
CREATE OPERATION
'''

@app.route('/add_recipe')
def add_recipe():
    '''
    Return the add_recipe.html template and inject the data into drop down menus
    '''
    return render_template("add_recipe.html",
        rating=rating_list,
        time=time_list,
        serves=serves_list,
        types=types_list,
        occasions=occasions_list,
        cuisines=cuisines_list,
        main_ing=main_ing_list)

@app.route('/insert_recipe', methods=["GET", "POST"])
def insert_recipe():
    '''
    Insert the new recipe entry into the database
    '''
    if request.method == 'POST':
        # Check if user has submitted an recipe
        if 'img' in request.files:
            # If user has submitted an image,
            # save to location and upload relative file path to database
            file_name = images.save(request.files['img'])
            file_path = "img/" + file_name
        else:
            # If no image, stock image file path will be stored in database
            file_path = "img/no-image-available.jpg"
        
        # Get today's date
        today = date.today()
        today_date = today.strftime("%d %B %Y")
        
        # Get session user details
        user = session['user'].lower()
        user_id = users_coll.find_one({"username": user})["_id"]
        
        insert = {
            "name": request.form.get("name").lower(),
            "rating_values": request.form.getlist(int("rating")),
            "prep_time": request.form.get("prep_time").lower(),
            "cook_time": request.form.get("cook_time").lower(),
            "serves": request.form.get("serves").lower(),
            "ingredients": request.form.getlist("ingredients"),
            "instructions": request.form.getlist("instructions"),
            "categories": {
                "type": request.form.get("type").lower(),
                "occasion": request.form.get("occasion").lower(),
                "cuisine": request.form.get("cuisine").lower(),
                "main_ing": request.form.get("main_ing").lower(),
            },
            "author": request.form.get("author").lower(),
            "img": file_path,
            "added_by": user_id,
            "added_date": today_date,
            "views": 0,
            "deleted": False
        }
        
        # Insert recipe dict (insert variable) into the database
        recipes_coll.insert_one(insert)
        
        # Flash message confirmation that recipe has been successfully added
        flash(Markup("Thanks " + user.capitalize() + ", your recipe has been added!"))
        
        return redirect(url_for('index'))

'''
READ OPERATION
'''

@app.route('/get_recipes')
def get_recipes():
    '''
    get recipes and display summary details in cards
    '''
    recipes = recipes_coll.find()
    return render_template("browse.html", recipes=recipes)

if __name__ == '__main__':
    app.run(host=os.getenv("IP", "0.0.0.0"),
            port=int(os.getenv("PORT", "5000")),
            debug=False)