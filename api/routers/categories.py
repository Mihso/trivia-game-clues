from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from typing import Union
import psycopg
import os
import bson
import pymongo

dbhost = os.environ['MONGOHOST']
dbname = os.environ['MONGODATABASE']
dbuser = os.environ['MONGOUSER']
dbpass = os.environ['MONGOPASSWORD']
mongo_str = f"mongodb://{dbuser}:{dbpass}@{dbhost}"

# Using routers for organization
# See https://fastapi.tiangolo.com/tutorial/bigger-applications/
router = APIRouter()


class CategoryIn(BaseModel):
    title: str


class CategoryOut(BaseModel):
    id: str
    title: str
    canon: bool


class  CategoryWithClueCount(BaseModel):
    id: str
    title: str
    canon: bool
    num_clues: int

class Categories(BaseModel):
    page_count: int
    categories: list[CategoryWithClueCount]


class Message(BaseModel):
    message: str

@router.get("/api/categories", response_model=Categories)
def categories_list(page: int = 0):
    client = pymongo.MongoClient(mongo_str)
    db = client[dbname]
    categories = db.categories.find().sort("title").skip(100*page).limit(100)
    categories = list(categories)
    for category in categories:
        count = db.command({
            "count": "clues",
            "query": { "category_id": category["_id"] }
        })
        category["num_clues"] = count["n"]
        category["id"] = str(category["_id"])
        del category["_id"]
    page_count = db.command({"count": "categories"})["n"] // 100
    return {
        "page_count": page_count,
        "categories": categories,
    }


@router.get(
    "/api/categories/{category_id}",
    response_model=CategoryOut,
    responses={404: {"model": Message}},
)
def get_category(category_id: Union[int, str]):
    client = pymongo.MongoClient(mongo_str)
    db = client[dbname]
    if isinstance(category_id, str):
        true_id = bson.objectid.ObjectId(category_id)
    else:
        true_id = category_id
    result = db.categories.find_one({"_id": true_id})
    result["id"] = str(result["_id"])
    del result["_id"]
    return result


@router.post(
    "/api/categories",
    response_model=CategoryOut,
    responses={409: {"model": Message}},
)
def create_category(category: CategoryIn):
    client = pymongo.MongoClient(mongo_str)
    db = client[dbname]
    cat = db.categories.insert_one({'title': category.title, "canon": False})
    return_cat = db.categories.find_one({'_id': cat.inserted_id})
    return_cat['id'] = str(cat.inserted_id)
    del return_cat["_id"]
    return return_cat
    # with psycopg.connect() as conn:
    #     with conn.cursor() as cur:
    #         try:
    #             # Uses the RETURNING clause to get the data
    #             # just inserted into the database. See
    #             # https://www.postgresql.org/docs/current/sql-insert.html
    #             cur.execute(
    #                 """
    #                 INSERT INTO categories (title, canon)
    #                 VALUES (%s, false)
    #                 RETURNING id, title, canon;
    #             """,
    #                 [category.title],
    #             )
    #         except psycopg.errors.UniqueViolation:
    #             # status values at https://github.com/encode/starlette/blob/master/starlette/status.py
    #             response.status_code = status.HTTP_409_CONFLICT
    #             return {
    #                 "message": "Could not create duplicate category",
    #             }
    #         row = cur.fetchone()
    #         record = {}
    #         for i, column in enumerate(cur.description):
    #             record[column.name] = row[i]
    #         return record


@router.put(
    "/api/categories/{category_id}",
    response_model=CategoryOut,
    responses={404: {"model": Message}},
)
def update_category(category_id: Union[int,str], category: CategoryIn, response: Response):
    client = pymongo.MongoClient(mongo_str)
    db = client[dbname]
    if isinstance(category_id, str):
        true_id = bson.objectid.ObjectId(category_id)
    else:
        true_id = category_id
    db.categories.update_one({"_id":true_id},{ '$set': {'title': category.title},})
    return_cat = db.categories.find_one({'_id': true_id})
    return_cat['id'] = return_cat['_id']
    del return_cat["_id"]
    return return_cat

    # with psycopg.connect() as conn:
    #     with conn.cursor() as cur:
    #         cur.execute(
    #             """
    #             UPDATE categories
    #             SET title = %s
    #             WHERE id = %s;
    #         """,
    #             [category.title, category_id],
    #         )
    return get_category(category_id, response)


@router.delete(
    "/api/categories/{category_id}",
    response_model=Message,
    responses={400: {"model": Message}},
)
def remove_category(category_id: Union[int,str]):
    client = pymongo.MongoClient(mongo_str)
    db = client[dbname]
    if isinstance(category_id, str):
        true_id = bson.objectid.ObjectId(category_id)
    else:
        true_id = category_id
    return_cat = db.categories.find_one({'_id': true_id})
    return_cat['id'] = return_cat['_id']
    del return_cat["_id"]
    db.categories.delete_one({"_id":true_id})
    return return_cat
    # with psycopg.connect() as conn:
    #     with conn.cursor() as cur:
    #         try:
    #             cur.execute(
    #                 """
    #                 DELETE FROM categories
    #                 WHERE id = %s;
    #             """,
    #                 [category_id],
    #             )
    #             return {
    #                 "message": "Success",
    #             }
    #         except psycopg.errors.ForeignKeyViolation:
    #             response.status_code = status.HTTP_400_BAD_REQUEST
    #             return {
    #                 "message": "Cannot delete category because it has clues",
    #             }
