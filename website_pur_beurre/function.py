# -*- coding: utf-8 -*-
"""
Contain the functions for run application.
"""

import psycopg2
from decimal import Decimal
from .config import config_project
import requests
import json
import os
from PIL import Image
from io import BytesIO
from urllib.parse import urlparse


def get_connection_db():
    """
    Get a connexion of database
    :return: connexion
    """
    if config_project['website_online']:
        info_db = urlparse(
            "postgres://kfwcgmbpgmbjqd:5f1fe7a35757878232fe2f8d3c42904617590c9e7790eed29ab0569576492a88@ec2-54-228-251-254.eu-west-1.compute.amazonaws.com:5432/da4492tmntkdhv")

        username = info_db.username
        password = info_db.password
        database = info_db.path[1:]
        hostname = info_db.hostname
        connexion = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname
        )
    else:
        connexion = psycopg2.connect(dbname=config_project['db']['dbname'],
                                     user=config_project['db']['user'],
                                     host=config_project['db']['host'],
                                     password=config_project['db']['password']
                                     )
    return connexion


def get_food_with_better_score(current_score):
    """
    Return a list (string) with better score than a score of food what we want replace
    :return:
    """
    list_better_score = []
    better_score_str = ''
    table_nutri_score = {'a': 5, 'b': 4, 'c': 3, 'd': 2, 'e': 1}
    score_my_food = table_nutri_score[current_score]
    if score_my_food == 5:
        list_better_score.append('a')
    else:
        for letter, score in table_nutri_score.items():
            if score > score_my_food and score not in [2, 1]:
                list_better_score.append(letter)
    for letter in list_better_score:
        better_score_str = better_score_str + "'" + letter + "',"
    # for delete the last comma :
    better_score_str = better_score_str[:-1]
    return better_score_str


def sort_dict(dict_no_sorted, sens="asc"):
    """
    This function sort a dict by theses keys.
    :return:
    """

    dict_sorted = {}
    lst_keys = sorted([int(key) for key, value in dict_no_sorted.items()])
    if sens == "desc":
        lst_keys = reversed(lst_keys)
    for k in lst_keys:
        value_sorted = dict_no_sorted[str(k)]
        dict_sorted[k] = value_sorted
    return dict_sorted


def make_dict_element(cursor, request, index=None, is_row=False, list_index=None):
    """
    Make a dictionnary with sorted keys (number who a user input) and them values
    for display a number with them value like this : 1 - value ..
    :return: Dictionnary with sorted keys
    """
    cursor.execute(request)
    list_element = {}
    num_element = 1
    list_name_element = []
    for element in cursor.fetchall():
        if not is_row:
            list_name_element.append(element[index])
        else:
            tuple_element = tuple((element[i] for i in list_index))
            list_name_element.append(tuple_element)

    for element in sorted(list_name_element):
        list_element[str(num_element)] = element
        num_element += 1

    list_element = sort_dict(list_element)
    return list_element


def clean_data(data):
    """
    In some case, some data content character which can not display on the application. This method
    remove bad character in a data name.
    :return: cleaned_data
    """
    if data[:3] in ['it:', 'fr:', 'en:', 'es:', 'de:', 'nl:']:
        data = data[3:]
    if data[:4] in [' it:', ' fr:', ' en:', ' es:', ' de:', ' nl:']:
        data = data[4:]

    if '\'' in data:
        data = data.replace('\'', '')
    if data[:1] == ' ':
        data = data[1:]

    return data


def decode_data(category):
    """
    Decode some character in category
    :param category:
    :return:
    """
    category = category.replace('œ', 'oe').replace('Œ', 'Oe')
    return category


def search_substitue_food(food, id_user=0):
    """
    Display all categories and when a user select a categorie, all food with
    them categorie is display. When user selected a food, all substitute of them
    food (with better score) is display and he can replace this food or not.
    :return:
    """
    connexion = get_connection_db()
    cursor = connexion.cursor()
    dict_with_substitute_food = {}

    query_category = "SELECT website_pur_beurre_Category.name " \
                     "FROM website_pur_beurre_Category, website_pur_beurre_FoodCategory, website_pur_beurre_Food " \
                     "WHERE website_pur_beurre_Category.id = website_pur_beurre_FoodCategory.category_id " \
                     "AND website_pur_beurre_Food.id = website_pur_beurre_FoodCategory.food_id " \
                     "AND website_pur_beurre_Food.name = '" + food + "'"

    cursor.execute("SELECT nutri_score FROM website_pur_beurre_Food WHERE name = '" + food + "';")
    list_betters_score = get_food_with_better_score(cursor.fetchone()[0])

    query_better_food = \
        "SELECT DISTINCT website_pur_beurre_Food.id, website_pur_beurre_Food.name, website_pur_beurre_Food.nutri_score " \
        ", website_pur_beurre_Food.web_link, website_pur_beurre_Food.link_food, website_pur_beurre_category.name " \
        "FROM website_pur_beurre_Category, website_pur_beurre_Food, website_pur_beurre_FoodCategory " \
        "WHERE website_pur_beurre_category.id = website_pur_beurre_FoodCategory.category_id " \
        "AND website_pur_beurre_food.id = website_pur_beurre_FoodCategory.food_id " \
        "AND website_pur_beurre_Category.name IN (" + query_category + ") " \
        "AND nutri_score IN ( " + list_betters_score + ") AND website_pur_beurre_Food.name != '" + food + "'" \
        "AND website_pur_beurre_Food.id NOT IN (SELECT website_pur_beurre_fooduser.food_id " \
                                               "FROM website_pur_beurre_fooduser " \
                                               "WHERE website_pur_beurre_fooduser.user_id = "+str(id_user)+") " \
        "ORDER BY website_pur_beurre_category.name LIMIT 10;"

    cursor.execute(query_better_food)
    num_food = 1
    for food in cursor.fetchall():
        category = food[5]
        if category not in dict_with_substitute_food.keys():
            dict_with_substitute_food[category] = []

        dict_with_substitute_food[category].append({
            'id': food[0],
            'name' : food[1],
            'nutri_score': food[2],
            'web_link': food[3],
            'image': str(food[0]) + '.png',
            'link_image' : food[4], # Only in mock mode
            'num_food': num_food % 3,
        })
        num_food += 1

    return dict_with_substitute_food


def get_user_foods(connexion, id_user):
    """
    Select the food what user selected.
    :return: list of the food what user replaced
    """
    cursor = connexion.cursor()
    query_select_food_user = "SELECT * " \
                             "FROM website_pur_beurre_Food, website_pur_beurre_FoodUser " \
                             "WHERE website_pur_beurre_Food.id = website_pur_beurre_FoodUser.food_id " \
                             "AND website_pur_beurre_FoodUser.id_user = " + str(id_user) + ";"
    cursor.execute(query_select_food_user)
    if cursor.fetchone() is None:
        return {}
    else:
        users_foods = make_dict_element(cursor,
                                             query_select_food_user,
                                             None,
                                             True,
                                             [1, 2, 3, 4])
        return users_foods


def put_food_in_db_by_mock():
    """
    This function use a json file (data_mock.json) for feed database wihout internet.
    :return:
    """
    connexion = get_connection_db()
    cursor = connexion.cursor()
    current_directory = os.path.dirname(os.path.realpath(__file__))
    path_json_file = current_directory + "\\data_mock.json"
    foods = json.load(open(path_json_file))

    for type_category, list_products in foods.items():
        for food in list_products:
            request_insert = "INSERT INTO website_pur_beurre_food (name, nutri_score, web_link, place, link_food) " \
                             "VALUES ('" + food['product_name'] + "', '" + food['nutrition_grades'] + "', '" + food['url'] \
                             + "', '" + food['purchase_places'] + "', '" + food['image_front_small_url'] + "');"
            cursor.execute(request_insert)
            connexion.commit()
            list_category = food['categories']
            for category in list_category:
                query_exist_category = "SELECT * FROM website_pur_beurre_category WHERE name ='" +category+"';"
                cursor.execute(query_exist_category)
                category_founded = cursor.fetchone()

                if category_founded is None:
                    query_insert_category = "INSERT INTO website_pur_beurre_category (name, type_category) " \
                                            "VALUES ('" + category + "', '" + type_category + "');"
                    cursor.execute(query_insert_category)
                    connexion.commit()

                query_get_food = "SELECT id FROM website_pur_beurre_Food WHERE name = '" + food['product_name'] + "';"

                cursor.execute(query_get_food)
                food_id = cursor.fetchone()[0]
                if food_id:
                    cursor.execute("SELECT id FROM website_pur_beurre_Category WHERE name = '" + category + "';")
                    for category_id in cursor.fetchall():
                        request_put_food_category = "INSERT INTO website_pur_beurre_FoodCategory" \
                                                    "(food_id, category_id) " \
                                                    "VALUES (" + str(food_id) + ", " \
                                                    + str(category_id[0]) + ");"
                        cursor.execute(request_put_food_category)
                        connexion.commit()
    connexion.commit()


def get_all_type_categories(in_test=False):
    """
    This function return a list with all type of category of food from openfoodfacts.
    You can see this list by this link : https://fr.openfoodfacts.org/categories/
    :param in_test:
    :return:
    """
    if in_test:
        list_type_category = ['desserts']
    else:
        categories_json = requests.get("https://fr.openfoodfacts.org/categories.json").json()
        list_categories_from_json = categories_json["tags"]
        list_type_category = []
        if config_project['website_online']:
            list_categories_from_json = list_categories_from_json[:300]
        for category in list_categories_from_json:
            if category["products"] > 1 and category["name"] != "":
                type_category = decode_data(category["name"])
                try:
                    print(type_category)
                except UnicodeEncodeError:
                    pass
                else:
                    list_type_category.append(type_category)

    return list_type_category


def load_image():
    """
    Load food's image and put them on static folder who name 'img'
    :return:
    """
    def save_image(id_food, link):
        image_food = Image.open(BytesIO(requests.get(link).content))
        image_food.thumbnail((128, 128), Image.ANTIALIAS)
        current_directory = os.path.dirname(os.path.realpath(__file__))
        image_food.save(current_directory + '\\static\\img\\foods\\' + str(id_food) + '.png', "PNG")

    connexion = get_connection_db()
    cursor = connexion.cursor()

    query_foods = "SELECT id, link_food FROM website_pur_beurre_food;"
    cursor.execute(query_foods)

    for food in cursor.fetchall():
        try:
            save_image(food[0], food[1])
        except:
            save_image(food[0], 'http://www.idfmoteurs.com/images/pas-image-disponible.png')
        else:
            pass


def create_json_mock():
    """
    DONT USE THIS FUNCTION PLEASE !
    This function create data_mock.json for have a json file with some foods for work wihout internet
    :return:
    """
    connexion_local = psycopg2.connect(dbname=config_project['db']['dbname'],
                                     user=config_project['db']['user'],
                                     host=config_project['db']['host'],
                                     password=config_project['db']['password']
                                     )

    dict_data_for_db = {}
    list_type_category = get_all_type_categories()
    cursor = connexion_local.cursor()
    i = 1
    for type_category in list_type_category:
        print(str(i) + '/' + str(len(list_type_category)) + " \n")
        try:
            type_category = type_category.replace('\'', '').lower()
            nb_food = 0
            request_foods = "SELECT distinct website_pur_beurre_food.name, website_pur_beurre_food.id, website_pur_beurre_food.nutri_score, " \
                            "website_pur_beurre_food.place, website_pur_beurre_food.link_food, website_pur_beurre_food.web_link " \
                            "FROM website_pur_beurre_food, website_pur_beurre_foodcategory, website_pur_beurre_category " \
                            "WHERE website_pur_beurre_food.id = website_pur_beurre_foodcategory.food_id " \
                            "AND website_pur_beurre_category.id = website_pur_beurre_foodcategory.category_id " \
                            "AND website_pur_beurre_category.type_category = '" + type_category + "' " \
                            "ORDER BY website_pur_beurre_food.name;"
            cursor.execute(request_foods)
            for food in cursor.fetchall():
                nb_food += 1
                if nb_food < 16:
                    if type_category not in dict_data_for_db.keys():
                        dict_data_for_db[type_category] = []

                    request_categories = "SELECT name " \
                                         "FROM website_pur_beurre_category " \
                                         "WHERE id IN (SELECT category_id " \
                                                       "FROM website_pur_beurre_foodcategory " \
                                                       "WHERE food_id = " + str(food[1]) + ");"
                    cursor.execute(request_categories)

                    dict_data_for_db[type_category].append({
                        'id': food[1],
                        'product_name': clean_data(food[0]),
                        'nutrition_grades' : food[2],
                        'purchase_places' : food[3],
                        'image_front_small_url': food[4],
                        'url': food[5],
                        'categories': [clean_data(category[0]) for category in cursor.fetchall()]
                    })
                else:
                    break
        except:
            pass
        i+=1

    clean_dict_data_for_db = {}
    for x, y in dict_data_for_db.items():
        try:
            print(x + ' -- ' + str(y))
        except:
            pass
        else:
            clean_dict_data_for_db[x] = y

    import pdb ; pdb.set_trace()
    json_data_for_db = json.dumps(clean_dict_data_for_db)
    f = open("data_mock.json", "w")
    f.write(json_data_for_db)
    f.close()


def feed_db_for_heroku():
    """
    Get json files for put elements in database of heroku.
    :return:
    """
    def connexion_db(type):
        if type == 'local':
            connexion = psycopg2.connect(dbname=config_project['db']['dbname'],
                                         user=config_project['db']['user'],
                                         host=config_project['db']['host'],
                                         password=config_project['db']['password']
                                         )

        elif type == 'heroku':
            info_db = urlparse("postgres://kfwcgmbpgmbjqd:5f1fe7a35757878232fe2f8d3c42904617590c9e7790eed29ab0569576492a88@ec2-54-228-251-254.eu-west-1.compute.amazonaws.com:5432/da4492tmntkdhv")
            username = info_db.username
            password = info_db.password
            database = info_db.path[1:]
            hostname = info_db.hostname
            connexion = psycopg2.connect(
                database=database,
                user=username,
                password=password,
                host=hostname
            )
        return connexion

    dict_data_for_db = {}
    list_type_category = get_all_type_categories()
    connexion_local = connexion_db('local')
    cursor = connexion_local.cursor()

    for type_category in list_type_category:
        type_category = type_category.replace('\'', '').lower()
        nb_food = 0
        request_foods = "SELECT distinct website_pur_beurre_food.name, website_pur_beurre_food.id, website_pur_beurre_food.nutri_score, " \
                        "website_pur_beurre_food.place, website_pur_beurre_food.link_food, website_pur_beurre_food.web_link " \
                        "FROM website_pur_beurre_food, website_pur_beurre_foodcategory, website_pur_beurre_category " \
                        "WHERE website_pur_beurre_food.id = website_pur_beurre_foodcategory.food_id " \
                        "AND website_pur_beurre_category.id = website_pur_beurre_foodcategory.category_id " \
                        "AND website_pur_beurre_category.type_category = '" + type_category + "' " \
                        "ORDER BY website_pur_beurre_food.name;"
        cursor.execute(request_foods)
        for food in cursor.fetchall():
            nb_food += 1
            if nb_food < 16:
                if type_category not in dict_data_for_db.keys():
                    dict_data_for_db[type_category] = []

                request_categories = "SELECT name " \
                                     "FROM website_pur_beurre_category " \
                                     "WHERE id IN (SELECT category_id " \
                                                   "FROM website_pur_beurre_foodcategory " \
                                                   "WHERE food_id = " + str(food[1]) + ");"
                cursor.execute(request_categories)

                dict_data_for_db[type_category].append({
                    'id': food[1],
                    'product_name': clean_data(food[0]),
                    'nutrition_grades' : food[2],
                    'purchase_places' : food[3],
                    'image_front_small_url': food[4],
                    'url': food[5],
                    'categories': [clean_data(category[0]) for category in cursor.fetchall()]
                })
            else:
                break

    connexion_heroku = connexion_db('heroku')
    cursor = connexion_heroku.cursor()

    list_food_in_db = []
    list_categories_in_db = []

    for type_category, list_products in dict_data_for_db.items():
        try:
            for food in list_products:
                if food['product_name'] not in list_food_in_db:
                    list_food_in_db.append(food['product_name'])
                    request_insert_food = "INSERT INTO website_pur_beurre_food (name, nutri_score, web_link, place, link_food) " \
                                     "VALUES ('" + food['product_name'] + "', '" + food['nutrition_grades'] + "', '" + food['url'] \
                                     + "', '" + food['purchase_places'] + "', '" + food['image_front_small_url'] + "');"
                    cursor.execute(request_insert_food)
                    connexion_heroku.commit()
                    list_category = food['categories']
                    for category in list_category:
                        print('-- ' + category)
                        if category not in list_categories_in_db:
                            list_categories_in_db.append(category)
                            query_insert_category = "INSERT INTO website_pur_beurre_category (name, type_category) " \
                                                    "VALUES ('" + category + "', '" + type_category + "');"
                            cursor.execute(query_insert_category)
                            connexion_heroku.commit()

                        query_get_food = "SELECT id FROM website_pur_beurre_Food WHERE name = '" + food['product_name'] + "';"
                        cursor.execute(query_get_food)
                        food_id = cursor.fetchone()[0]
                        if food_id:
                            cursor.execute("SELECT id FROM website_pur_beurre_Category WHERE name = '" + category + "';")
                            for category_id in cursor.fetchall():
                                request_put_food_category = "INSERT INTO website_pur_beurre_FoodCategory" \
                                                            "(food_id, category_id) " \
                                                            "VALUES (" + str(food_id) + ", " \
                                                            + str(category_id[0]) + ");"
                                cursor.execute(request_put_food_category)
                                connexion_heroku.commit()
                    connexion_heroku.commit()
        except:
            pass


def put_food_in_db():
    """
    Get json files for put elements in database.
    :return:
    """

    print('**************************************')

    connexion = get_connection_db()
    in_test = False

    list_categories_in_db = []
    list_type_category = get_all_type_categories(in_test)

    for type_category in list_type_category:
        print(type_category)
        print('**************************************')
        try:
            cursor = connexion.cursor()

            type_category = type_category.lower()
            try:
                first_page = requests.get('https://fr-en.openfoodfacts.org/category/'+type_category+'/1.json').json()
            except:
                pass
            else:
                page_size = first_page['page_size']
                count_element = first_page['count']
                total_page = Decimal(round(count_element / page_size, 0)) + 2
                if config_project['website_online']:
                    total_page = 4
                    if count_element < 4:
                        total_page = Decimal(round(count_element / page_size, 0)) + 2

                food_category = {}

                for num_page in range(1, int(total_page)):
                    foods = requests.get(
                        'https://fr-en.openfoodfacts.org/category/'+type_category+'/' + str(num_page)+'.json').json()

                    for food in foods['products']:
                        # Products wihout nutrition grades not will insert in database.
                        try:
                            if 'nutrition_grades' in food.keys():
                                if 'product_name_fr' not in food.keys():
                                    product_name = clean_data(food['product_name']).lower()
                                else:
                                    product_name = clean_data(food['product_name_fr']).lower()
                                try:
                                    print(decode_data(product_name))
                                except UnicodeEncodeError:
                                    pass
                                else:
                                    product_place = ''
                                    if 'purchase_places' in food.keys():
                                        product_place = clean_data(product_place)

                                    check_if_food_in_db = "SELECT count(*) FROM website_pur_beurre_Food WHERE name = '" + product_name + "';"
                                    cursor.execute(check_if_food_in_db)
                                    food_getted = cursor.fetchone()[0]

                                    if food_getted == 0:
                                        if product_name != '':
                                            link_food = 'http://www.idfmoteurs.com/images/pas-image-disponible.png'
                                            if food.get('image_front_small_url'):
                                                link_food = food['image_front_small_url']

                                            request_insert = "INSERT INTO website_pur_beurre_food (name, nutri_score, web_link, place, link_food) " \
                                                             "VALUES ('" + product_name + "', '" \
                                                             + food['nutrition_grades'] + "', '"\
                                                             + food['url'] + "', '" + product_place + "', '" + link_food + "');"
                                            cursor.execute(request_insert)

                                            food_category[product_name] = []
                                            # for each product, we get all categories which product is associate
                                            list_categories = food['categories'].split(',')
                                            list_categories = [category.lower() for category in list_categories]
                                            for category in list_categories:
                                                category = clean_data(category)
                                                if category not in list_categories_in_db:
                                                    # We check if category is not exist for insert it
                                                    list_categories_in_db.append(category)
                                                    type_category = type_category.replace('\'', '')
                                                    query_insert_category = "INSERT INTO website_pur_beurre_category (name, type_category) " \
                                                                            "VALUES ('" + category + "', '"+type_category.lower()+"');"
                                                    cursor.execute(query_insert_category)
                                                food_category[product_name].append(category)

                                            connexion.commit()

                                            query_get_food = "SELECT id FROM website_pur_beurre_Food WHERE name = '" + product_name + "';"
                                            cursor.execute(query_get_food)
                                            food_id = cursor.fetchone()[0]
                                            if food_id:

                                                for category in food_category[product_name]:
                                                    cursor.execute(
                                                        "SELECT id FROM website_pur_beurre_Category WHERE name = '" + category.lower() + "';")
                                                    category_id = cursor.fetchone()[0]
                                                    if category_id:
                                                        cursor.execute("SELECT * "
                                                                       "FROM website_pur_beurre_FoodCategory "
                                                                       "WHERE food_id = '" + str(food_id) + "'"
                                                                       "AND category_id = '" + str(category_id) + "';")
                                                        # We check if we don't have the same food associate at the same category
                                                        if cursor.fetchone() is None:
                                                            request_put_food_category = "INSERT INTO website_pur_beurre_FoodCategory" \
                                                                                                                    "(food_id, category_id) " \
                                                                                                            "VALUES (" + str(food_id) + ", " \
                                                                                                            + str(category_id) + ");"
                                                            cursor.execute(request_put_food_category)
                                                            connexion.commit()
                        except:
                            pass
        except:
            pass


def delete_data_db():
    """
    Delete all data of database.
    :return:
    """
    connexion = get_connection_db()
    cursor = connexion.cursor()
    request_delete = "DELETE FROM website_pur_beurre_foodcategory;" \
                     "DELETE FROM website_pur_beurre_fooduser;" \
                     "DELETE FROM website_pur_beurre_food;" \
                     "DELETE FROM website_pur_beurre_category;"
    cursor.execute(request_delete)
    connexion.commit()
