from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from typing import Union
import routers
import os
import bson
import pymongo
# from categories import CategoryOut
import psycopg

dbhost = os.environ['MONGOHOST']
dbname = os.environ['MONGODATABASE']
dbuser = os.environ['MONGOUSER']
dbpass = os.environ['MONGOPASSWORD']
mongo_str = f"mongodb://{dbuser}:{dbpass}@{dbhost}"
# Using routers for organization
# See https://fastapi.tiangolo.com/tutorial/bigger-applications/
router = APIRouter()


class ClueIn(BaseModel):
    id: str


class ClueOut(BaseModel):
    id: str
    answer: str
    question: str
    value: int
    invalid_count: int
    category: object
    canon: bool

class Clues(BaseModel):
    page_count: int
    clues: list[ClueOut]


class Message(BaseModel):
    message: str


@router.get("/api/clues", response_model=Clues)
def clues_list(page: int = 0):
    client = pymongo.MongoClient(mongo_str)
    db = client[dbname]
    clues = db.clues.find({'invalid_count': {"$eq":0}}).sort("_id").skip(100*page).limit(100)
    clues = list(clues)
    for clue in clues:
        category = db.categories.find_one({"_id": clue["category_id"]})
        db.categories.find()
        clue["id"] = str(clue["_id"])
        clue["category"] = category
        del clue["_id"]
        del clue["category_id"]
    page_count = db.command({"count": "clues"})["n"] // 100
    return {
        "page_count": page_count,
        "clues": clues,
    }
    # # Uses the environment variables to connect
    # # In development, see the docker-compose.yml file for
    # #   the PG settings in the "environment" section
    # with psycopg.connect() as conn:
    #     with conn.cursor() as cur:
    #         cur.execute(
    #             f"""
    #             SELECT clues.id, 
    #             clues.answer, 
    #             clues.question, 
    #             clues.value, 
    #             clues.invalid_count,
    #             clues.canon,
    #             clues.category_id AS category,
    #             categories.id AS id,
    #             categories.title, 
    #             categories.canon AS canon
    #             FROM categories
    #             JOIN clues
    #                 ON (categories.id = clues.category_id)
    #             WHERE clues.invalid_count = 0
    #             LIMIT 100 OFFSET %s
    #         """,
    #             [page * 100],
    #         )

    #         results = []
    #         for row in cur.fetchall():
    #             record = {}
    #             grouping = False
    #             category_object = {}
    #             for i, column in enumerate(cur.description):
    #                 if grouping == False:
    #                     record[column.name] = row[i]
    #                 else:
    #                     category_object[column.name] = row[i]
    #                 if column.name == "category":
    #                     grouping = True
    #             record["category"] = category_object
    #             results.append(record)

    #         cur.execute(
    #             """
    #             SELECT COUNT(*) FROM clues;
    #         """
    #         )
    #         raw_count = cur.fetchone()[0]
    #         page_count = (raw_count // 100) + 1

    #         return Clues(page_count=page_count, categories=results)


@router.get(
    "/api/clues/{clue_id}",
    response_model=ClueOut,
    responses={404: {"model": Message}},
)
def get_clue(clue_id: Union[int, str]):
    client = pymongo.MongoClient(mongo_str)
    db = client[dbname]
    if isinstance(clue_id,int):
        true_id = int(clue_id)
    else:
        true_id = clue_id
    result = db.clues.find_one({"$and": [{"_id": true_id}, {'invalid_count': {"$eq": 0}}]})
    result["id"] = str(result["_id"])
    del result["_id"]
    category = db.categories.find_one({"_id": result["category_id"]})
    db.categories.find()
    result["category"] = category
    del result["category_id"]
    return result

    # with psycopg.connect() as conn:
    #     with conn.cursor() as cur:
    #         cur.execute(
    #             f"""
    #             SELECT clues.id, 
    #             clues.answer, 
    #             clues.question, 
    #             clues.value, 
    #             clues.invalid_count,
    #             clues.canon,
    #             clues.category_id AS category,
    #             categories.id AS id,
    #             categories.title, 
    #             categories.canon AS canon
    #             FROM categories
    #             JOIN clues
    #                 ON (categories.id = clues.category_id)
    #             WHERE clues.id = %s AND clues.invalid_count = 0;
    #         """,
    #             [clue_id],
    #         )
    #         row = cur.fetchone()
    #         if row is None:
    #             response.status_code = status.HTTP_404_NOT_FOUND
    #             return {"message": "Clue not found"}
    #         record = {}
    #         grouping = False
    #         category_object = {}
    #         for i, column in enumerate(cur.description):
    #             if grouping == False:
    #                 record[column.name] = row[i]
    #             else:
    #                 category_object[column.name] = row[i]
    #             if column.name == "category":
    #                 grouping = True
    #         record["category"] = category_object
    #         return record

@router.get(
    "/api/random-clue",
    response_model=ClueOut,
    responses={404: {"model": Message}},
)
def get_random_clue(valid: bool = True):
    client = pymongo.MongoClient(mongo_str)
    db = client[dbname]
    if valid == True:
        result = list(db.clues.aggregate([{"$match": {"invalid_count": {"$eq": 0}}},{"$sample": {"size": 1}}]))[0]
    else:
        result = list(db.clues.aggregate([{"$sample": {"size": 1}}]))[0]
        
    result["id"] = str(result["_id"])
    del result["_id"]
    category = db.categories.find_one({"_id": result["category_id"]})
    db.categories.find()
    result["category"] = category
    del result["category_id"]
    return result

    # with psycopg.connect() as conn:
    #     with conn.cursor() as cur:
    #         if valid == True:
    #             cur.execute(
    #                 f"""
    #                 SELECT clues.id, 
    #                 clues.answer, 
    #                 clues.question, 
    #                 clues.value, 
    #                 clues.invalid_count,
    #                 clues.canon,
    #                 clues.category_id AS category,
    #                 categories.id AS id,
    #                 categories.title, 
    #                 categories.canon AS canon
    #                 FROM categories
    #                 JOIN clues
    #                     ON (categories.id = clues.category_id)
    #                 WHERE clues.invalid_count = 0
    #                 ORDER BY RANDOM() LIMIT 1;
    #             """,
    #                 [],
    #             )
    #         else:
    #             cur.execute(
    #                 f"""
    #                 SELECT clues.id, 
    #                 clues.answer, 
    #                 clues.question, 
    #                 clues.value, 
    #                 clues.invalid_count,
    #                 clues.canon,
    #                 clues.category_id AS category,
    #                 categories.id AS id,
    #                 categories.title, 
    #                 categories.canon AS canon
    #                 FROM categories
    #                 JOIN clues
    #                     ON (categories.id = clues.category_id)
    #                 ORDER BY RANDOM() LIMIT 1;
    #             """,
    #                 [],
    #             )
    #         row = cur.fetchone()
    #         if row is None:
    #             response.status_code = status.HTTP_404_NOT_FOUND
    #             return {"message": "Clue not found"}
    #         record = {}
    #         grouping = False
    #         category_object = {}
    #         for i, column in enumerate(cur.description):
    #             if grouping == False:
    #                 record[column.name] = row[i]
    #             else:
    #                 category_object[column.name] = row[i]
    #             if column.name == "category":
    #                 grouping = True
    #         record["category"] = category_object
    #         return record
# @router.post(
#     "/api/clues",
#     response_model=ClueOut,
#     responses={409: {"model": Message}},
# )
# def create_clue(category: ClueIn, response: Response):
#     with psycopg.connect() as conn:
#         with conn.cursor() as cur:
#             try:
#                 # Uses the RETURNING clause to get the data
#                 # just inserted into the database. See
#                 # https://www.postgresql.org/docs/current/sql-insert.html
#                 cur.execute(
#                     """
#                     INSERT INTO categories (title, canon)
#                     VALUES (%s, false)
#                     RETURNING id, title, canon;
#                 """,
#                     [category.title],
#                 )
#             except psycopg.errors.UniqueViolation:
#                 # status values at https://github.com/encode/starlette/blob/master/starlette/status.py
#                 response.status_code = status.HTTP_409_CONFLICT
#                 return {
#                     "message": "Could not create duplicate category",
#                 }
#             row = cur.fetchone()
#             record = {}
#             for i, column in enumerate(cur.description):
#                 record[column.name] = row[i]
#             return record


# @router.put(
#     "/api/clues/{category_id}",
#     response_model=ClueOut,
#     responses={404: {"model": Message}},
# )
# def update_clue(category_id: int, category: ClueIn, response: Response):
#     with psycopg.connect() as conn:
#         with conn.cursor() as cur:
#             cur.execute(
#                 """
#                 UPDATE categories
#                 SET title = %s
#                 WHERE id = %s;
#             """,
#                 [category.title, category_id],
#             )
#     return get_category(category_id, response)


@router.put(
    "/api/clues/{clue_id}",
    response_model=ClueOut,
    responses={404: {"model": Message}},
)
def remove_clue(clue_id: Union[int, str]):
    client = pymongo.MongoClient(mongo_str)
    db = client[dbname]
    if isinstance(clue_id, int):
        true_id = int(clue_id)
    else:
        true_id = clue_id
    db.clues.update_one({"_id":true_id},{ '$inc': {'invalid_count': 1}})
    return_cat = db.clues.find_one({'_id': true_id})
    return_cat['id'] = return_cat['_id']
    del return_cat["_id"]
    return return_cat
    # with psycopg.connect() as conn:
    #     with conn.cursor() as cur:
    #         try:
    #             cur.execute(
    #                 f"""
    #                 UPDATE clues
    #                 SET invalid_count = invalid_count + 1

    #                 WHERE id = %s;
    #             """,
    #                 [clue_id],
    #             )
    #             return get_clue(clue_id, response)
    #         except psycopg.errors.ForeignKeyViolation:
    #             response.status_code = status.HTTP_404_BAD_REQUEST
    #             return {
    #                 "message": "Cannot delete clue",
    #             }
