import json
import math
import html
import re
from flask import (
    Blueprint, render_template, redirect, request, session,
    url_for, flash, Markup)
from bson.objectid import ObjectId
from datetime import date
from flask_uploads import UploadSet, configure_uploads, IMAGES
from cookbook.utils import (
    recipes_coll, users_coll, rating_list, time_list, serves_list,
    types_list, occasions_list, cuisines_list, main_ing_list,
    find_recipe, get_username)
from cookbook import images

# Blueprint instance to recipes route
recipes = Blueprint("recipes", __name__)


'''
CREATE OPERATION
'''


@recipes.route('/add_recipe')
def add_recipe():
    '''
    Return add_recipe.html template and inject data into drop down menus
    '''
    return render_template(
                        "add_recipe.html",
                        rating=rating_list,
                        time=time_list,
                        serves=serves_list,
                        types=types_list,
                        occasions=occasions_list,
                        cuisines=cuisines_list,
                        main_ing=main_ing_list
                        )


@recipes.route('/insert_recipe', methods=["GET", "POST"])
def insert_recipe():
    '''
    Insert the new recipe entry into the database
    Add the recipe id into the user's added list in users_coll
    '''
    if request.method == 'POST':
        # Check if user has submitted an image
        # If filepath field is an empty string, no image is present
        if request.form.get("filepath") != "":
            # If user has submitted a new image,
            # save to location and upload relative file path to database
            file_name = images.save(request.files['image'])
            file_path = "img/" + file_name
        else:
            # If no image, stock image file path will be stored in database
            file_path = "img/no-image-available.jpg"

        # Get today's date
        today = date.today()
        today_date = today.strftime("%d %B %Y")

        # Get session user details
        user = session['user'].lower()
        user_id = get_username(user)["_id"]

        insert = {
            "name": request.form.get("name").lower(),
            "rating_values": [
                int(request.form.get("rating"))
            ],
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
            "last_edited_date": "",
            "views": 0,
            "likes": 0,
            "deleted": False
        }

        # Insert recipe dict (insert variable) into database and get new ID
        new_id = recipes_coll.insert_one(insert)

        # Add the new recipe ID to the users collection for that user
        users_coll.update_one(
            {"_id": ObjectId(user_id)},
            {"$push": {"added_recipes": new_id.inserted_id}})

        # Flash message confirmation that recipe has been successfully added
        flash(Markup("Thanks \
                    <span class='message-helper bold italic'>" + user.capitalize() + "</span>, \
                    your recipe has been added!"))

        return redirect(url_for('recipes.get_recipes', page=1))


'''
READ OPERATION
'''


@recipes.route('/get_recipes/<page>', methods=["GET", "POST"])
def get_recipes(page):
    '''
    Get all recipes and display summary details in cards
    '''
    # Number of results to skip when searching recipes_coll - for pagination
    skip_count = (int(page) - 1) * 8

    # FILTERED RESULTS WITH NO SEARCH
    if request.method == 'POST':
        # Get user's submission from filter form and put into a dictionary
        form_input = request.form.to_dict()

        # Build the filter query
        # Message if user doesn't select any filters before submitting form
        if len(form_input) == 0:
            flash(Markup("You haven't selected any filter options. \
                        Please choose a category to filter."))
            return redirect(url_for('recipes.get_recipes', page=1))

        # Filter query if one option is selected from the form
        elif len(form_input) == 1:
            for k, v in form_input.items():
                cat_one = 'categories.' + k
                val_one = v.lower()

                # Only include recipes with "deleted" value of False
                filter_query = ({'$and': [{cat_one: val_one},
                                {"deleted": False}]})

        # Filter query if two options are selected from the form
        elif len(form_input) == 2:
            if 'type' in form_input and 'occasion' in form_input:
                cat_one = 'categories.type'
                val_one = str(form_input['type']).lower()
                cat_two = 'categories.occasion'
                val_two = str(form_input['occasion']).lower()
            elif 'type' in form_input and 'cuisine' in form_input:
                cat_one = 'categories.type'
                val_one = str(form_input['type']).lower()
                cat_two = 'categories.cuisine'
                val_two = str(form_input['cuisine']).lower()
            elif 'type' in form_input and 'main_ing' in form_input:
                cat_one = 'categories.type'
                val_one = str(form_input['type']).lower()
                cat_two = 'categories.main_ing'
                val_two = str(form_input['main_ing']).lower()
            elif 'occasion' in form_input and 'cuisine' in form_input:
                cat_one = 'categories.occasion'
                val_one = str(form_input['occasion']).lower()
                cat_two = 'categories.cuisine'
                val_two = str(form_input['cuisine']).lower()
            elif 'occasion' in form_input and 'main_ing' in form_input:
                cat_one = 'categories.occasion'
                val_one = str(form_input['occasion']).lower()
                cat_two = 'categories.main_ing'
                val_two = str(form_input['main_ing']).lower()
            else:
                cat_one = 'categories.cuisine'
                val_one = str(form_input['cuisine']).lower()
                cat_two = 'categories.main_ing'
                val_two = str(form_input['main_ing']).lower()

            # Only include recipes with "deleted" value of False
            filter_query = ({'$and': [{cat_one: val_one},
                            {cat_two: val_two},
                            {"deleted": False}]})

        # Filter query if three options are selected from the form
        elif len(form_input) == 3:
            if 'type' in form_input\
                and 'occasion' in form_input\
                    and 'cuisine' in form_input:
                        cat_one = 'categories.type'
                        val_one = str(form_input['type']).lower()
                        cat_two = 'categories.occasion'
                        val_two = str(form_input['occasion']).lower()
                        cat_three = 'categories.cuisine'
                        val_three = str(form_input['cuisine']).lower()
            elif 'type' in form_input\
                and 'occasion' in form_input\
                    and 'main_ing' in form_input:
                        cat_one = 'categories.type'
                        val_one = str(form_input['type']).lower()
                        cat_two = 'categories.occasion'
                        val_two = str(form_input['occasion']).lower()
                        cat_three = 'categories.main_ing'
                        val_three = str(form_input['main_ing']).lower()
            elif 'type' in form_input\
                and 'cuisine' in form_input\
                    and 'main_ing' in form_input:
                        cat_one = 'categories.type'
                        val_one = str(form_input['type']).lower()
                        cat_two = 'categories.cuisine'
                        val_two = str(form_input['cuisine']).lower()
                        cat_three = 'categories.main_ing'
                        val_three = str(form_input['main_ing']).lower()
            else:
                cat_one = 'categories.occasion'
                val_one = str(form_input['occasion']).lower()
                cat_two = 'categories.cuisine'
                val_two = str(form_input['cuisine']).lower()
                cat_three = 'categories.main_ing'
                val_three = str(form_input['main_ing']).lower()

            # Only include recipes with "deleted" value of False
            filter_query = ({'$and': [{cat_one: val_one},
                            {cat_two: val_two},
                            {cat_three: val_three},
                            {"deleted": False}]})

        # Filter query if all options are selected from the form
        elif len(form_input) == 4:
            cat_one = 'categories.type'
            val_one = str(form_input['type']).lower()
            cat_two = 'categories.occasion'
            val_two = str(form_input['occasion']).lower()
            cat_three = 'categories.cuisine'
            val_three = str(form_input['cuisine']).lower()
            cat_four = 'categories.main_ing'
            val_four = str(form_input['main_ing']).lower()

            # Only include recipes with "deleted" value of False
            filter_query = ({'$and': [{cat_one: val_one},
                            {cat_two: val_two},
                            {cat_three: val_three},
                            {cat_four: val_four},
                            {"deleted": False}]})

        recipes = recipes_coll.find(filter_query)

        # Pagination for filtered results
        paginated_recipes = recipes_coll.find(filter_query)\
                                        .sort([("likes", -1),
                                               ('name', 1),
                                               ("_id", 1)])\
                                        .skip(skip_count).limit(8)

    # ALL RECIPES WITH NO SEARCH OR FILTERS
    else:
        # Only include recipes with "deleted" value of False
        recipes = recipes_coll.find({"deleted": False})

        # Pagination for all recipes
        paginated_recipes = recipes_coll.find({"deleted": False})\
                                        .sort([("likes", -1),
                                               ('name', 1),
                                               ("_id", 1)])\
                                        .skip(skip_count).limit(8)

    if recipes:
        recipes_count = recipes.count()
    else:
        recipes_count = 0

    total_pages = int(math.ceil(recipes_count/8.0))

    if recipes_count == 0:
        page = 0

    # RESULTS USING THE SEARCH FORM
    # Args variable to get args from the form
    args = request.args.get

    # Set search_word variable
    if args(str("search")):
        search_word = args(str("search"))
    else:
        search_word = ""

    if not search_word:
        search_results = ""
    else:
        # Only include recipes with "deleted" value of False
        search_results = recipes_coll.find(
                {'$and': [{"$text": {"$search": search_word}},
                          {"deleted": False}]})\
                          .sort([("likes", -1), ('name', 1)])

    # Count the search_results
    if search_results:
        search_results_count = search_results.count()
    else:
        search_results_count = 0

    return render_template(
                        "browse.html",
                        page=page,
                        recipes=paginated_recipes,
                        recipes_count=recipes_count,
                        search_results=search_results,
                        search_results_count=search_results_count,
                        total_pages=total_pages,
                        types=types_list,
                        occasions=occasions_list,
                        cuisines=cuisines_list,
                        main_ing=main_ing_list
                        )


@recipes.route('/recipe/<recipe_id>')
def recipe(recipe_id):
    '''
    Gets details for particular recipe_id that the user clicked on browse.html
    Routes the user to the recipes.html page with details for that recipe_id
    Each time the recipe is viewed, it increments the 'views' field by one
    '''
    recipe = find_recipe(recipe_id)

    try:
        # Get the user's liked_recipes list if a user is logged in
        user = session["user"].lower()
        liked_recipes = get_username(user)["liked_recipes"]
    except:
        # Create an empty liked_recipes list if no user is logged in
        liked_recipes = []

    # Increment 'views' field by 1 each time the recipe is viewed
    recipes_coll.update_one({"_id": ObjectId(recipe_id)},
                            {"$inc": {"views": 1}})

    # Convert added_by ObjectId to username value - verify against session user
    added_by = users_coll.find_one(
        {"_id": ObjectId(recipe.get("added_by"))})["username"]

    return render_template(
                        "recipes.html",
                        recipe=recipe,
                        ratings=rating_list,
                        added_by=added_by,
                        liked_recipes=liked_recipes
                        )


'''
UPDATE OPERATION
'''


@recipes.route('/edit_recipe/<recipe_id>')
def edit_recipe(recipe_id):
    '''
    Route user to edit_recipe.html and inject existing data into the form
    Give users the ability to amend the recipe details
    '''
    recipe = find_recipe(recipe_id)

    return render_template(
                        "edit_recipe.html",
                        recipe=recipe,
                        ratings=rating_list,
                        time=time_list,
                        serves=serves_list,
                        types=types_list,
                        occasions=occasions_list,
                        cuisines=cuisines_list,
                        main_ing=main_ing_list
                        )


@recipes.route('/update_recipe/<recipe_id>', methods=["POST"])
def update_recipe(recipe_id):
    '''
    Update existing database record with the new form values
    '''
    if request.method == 'POST':

        # Get the recipe_id
        recipe = find_recipe(recipe_id)

        # Convert ObjectId to username value - verify against session user
        added_by = recipe.get("added_by")

        # Check if user has submitted an image
        if request.form.get("filepath") == recipe.get("img"):
            # If no new image is added by the user (URL unchanged)
            file_path = recipe.get("img")
        elif request.form.get("filepath") != "":
            # If user has submitted a new image,
            # save to location and upload relative file path to database
            file_name = images.save(request.files['image'])
            file_path = "img/" + file_name
        else:
            # If user removes image, store stock image file path in database
            file_path = "img/no-image-available.jpg"

        # Get rating values
        rating_values = recipe.get("rating_values")

        # Get added date
        added_date = recipe.get("added_date")

        # Get last edited date
        today = date.today()
        last_edited_date = today.strftime("%d %B %Y")

        # Get number of views and decrement by 1
        # Resolves bug of it being incremented when redirected to recipes.html
        views = recipe.get("views")
        decrement_views = views - 1

        # Get number of likes
        likes = recipe.get("likes")

        # Get session user details
        user = session['user'].capitalize()

        # Update new values in the database
        recipes_coll.update({"_id": ObjectId(recipe_id)}, {
            "name": request.form.get("name").lower(),
            "rating_values": rating_values,
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
            "added_by": added_by,
            "added_date": added_date,
            "last_edited_date": last_edited_date,
            "views": decrement_views,
            "likes": likes,
            "deleted": False
        })

        # Flash message confirmation that recipe has been successfully added
        flash(Markup("Thanks \
                    <span class='message-helper bold italic'>" + user.capitalize() + "</span>, \
                    this recipe has been successfully edited!"))

        return redirect(url_for('recipes.recipe',
                                recipe_id=recipe_id))


'''
DELETE OPERATION
'''


@recipes.route('/remove_recipe/<recipe_id>')
def remove_recipe(recipe_id):
    '''
    Changes 'deleted' value in recipes_coll to 'True'
    Ensures that recipe remains in the DB but is removed from the front end
    '''
    # Change the deleted field to 'True'
    recipes_coll.update_one({"_id": ObjectId(recipe_id)},
                            {"$set": {"deleted": True}})

    # Get session user details
    user = session['user'].lower()
    # Remove the recipe ID from that particular users' added_recipes list
    users_coll.find_one_and_update(
        {"username": user},
        {"$pull": {"added_recipes": ObjectId(recipe_id)}})
    # Remove the recipe ID from all users' liked_recipes list
    users_coll.update_many(
        {},
        {"$pull": {"liked_recipes": ObjectId(recipe_id)}})

    # Flash message confirmation that recipe has been successfully added
    flash(Markup("Thanks \
                <span class='message-helper bold italic'>" +
                 user.capitalize() + "</span>, \
                 this recipe has been successfully deleted!"))

    return redirect(url_for('recipes.get_recipes',
                            page=1,
                            recipe_id=recipe_id))


'''
RATE RECIPE
'''


@recipes.route('/rate/<recipe_id>', methods=["GET", "POST"])
def rate(recipe_id):
    '''
    Allows the user to rate the recipe
    Pushes rating value into rating_values list in recipes_coll
    '''
    username = session["user"]
    # Push rating from form into the rating_values field in the relevant record
    recipes_coll.update_one(
                {"_id": ObjectId(recipe_id)},
                {"$push": {"rating_values": int(request.form.get("rating"))}})

    # Decrement number of views by 1
    # Resolves bug of it being incremented when redirected to recipes.html
    recipes_coll.update_one({"_id": ObjectId(recipe_id)},
                            {"$inc": {"views": -1}})

    # Flash message confirmation that recipe has been successfully added
    flash(Markup("Thanks for rating this recipe \
                <span class='message-helper bold italic'>" +
                 username.capitalize() + "</span>!"))

    return redirect(url_for('recipes.recipe',
                            recipe_id=recipe_id))


'''
LIKE/UNLIKE RECIPE
'''


@recipes.route('/like_recipe/<recipe_id>')
def like_recipe(recipe_id):
    '''
    Allows the user to like a particular recipe
    The recipe_id is added to user's liked_recipes list in users_coll
    The 'likes' field in the recipes collection is incremented by 1
    The 'views' field in the recipes collection is decremented by 1
    '''

    # Add the liked recipe ID to the users collection for that user
    user = session['user'].lower()
    users_coll.find_one_and_update(
        {"username": user},
        {"$push": {"liked_recipes": ObjectId(recipe_id)}})

    # Increment 'likes' field in recipes_coll by 1 for each like
    recipes_coll.update_one({"_id": ObjectId(recipe_id)},
                            {"$inc": {"likes": 1, "views": -1}})

    # Flash message confirmation that the user successfully liked the recipe
    flash(Markup("Thanks \
                <span class='message-helper bold italic'>" + user.capitalize() + "</span>, \
                this recipe has been added to your 'Liked' list!"))

    return redirect(request.referrer)


@recipes.route('/unlike_recipe/<recipe_id>')
def unlike_recipe(recipe_id):
    '''
    Allows the user to unlike a particular recipe
    The recipe_id is removed from user's liked_recipes list in the users_coll
    The 'likes' field in the recipes collection is decremented by 1
    The 'views' field in recipes_collis decremented by 1,
    only if the recipe is unliked from recipe.html
    '''

    # Remove the liked recipe ID to the users collection for that user
    user = session['user'].lower()
    users_coll.find_one_and_update(
        {"username": user},
        {"$pull": {"liked_recipes": ObjectId(recipe_id)}})

    # Decrement 'likes' field in recipes_coll by 1 each time recipe is unliked
    recipes_coll.update_one(
        {"_id": ObjectId(recipe_id)},
        {"$inc": {"likes": -1}})

    # Only decrement views if the user unlikes a recipe on the recipe.html page
    # Resolves bug where views were decremented when
    # the user unlikes a recipe in profile.html
    if request.path == 'recipe':
        recipes_coll.update_one(
            {"_id": ObjectId(recipe_id)},
            {"$inc": {"views": -1}})

    # Flash message confirmation that the user successfully liked the recipe
    flash(Markup("Thanks \
                <span class='message-helper bold italic'>" +
                 user.capitalize() + "</span>, \
                 this recipe has been removed from your 'Liked' list!"))

    return redirect(request.referrer)
