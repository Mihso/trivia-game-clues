from datetime import datetime
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

class GameIn(BaseModel):
    id: Union[str, int]


class CategoryOut(BaseModel):
    id: str
    title: str

class ClueOut(BaseModel):
    id: str
    answer: str
    question: str
    value: int
    invalid_count: int
    category: CategoryOut

class GameOut(BaseModel):
    id: Union[str, int]
    episode_id: int
    aired: str
    canon: bool
    total_amount_won: int

class CustomGameIn(BaseModel):
    created_on: str

class CustomGameOut(BaseModel):
    id: str
    created_on: datetime
    clues: list[ClueOut]

class Message(BaseModel):
    message: str

class Games(BaseModel):
    games: list[GameOut]

@router.get(
    "/api/games/{game_id}",
    response_model=GameOut,
    responses={404: {"model": Message}},
)
def get_game(game_id: Union[int, str]):
    client = pymongo.MongoClient(mongo_str)
    db = client[dbname]
    if isinstance(game_id, str):
        true_id = bson.objectid.ObjectId(game_id)
    else:
        true_id = game_id
    result = db.games.find_one({"_id": true_id})
    result["id"] = str(result["_id"])
    clue = db.command(
       {
            "count": "clues",
            "query": {"game_id": result['_id']}
        }
    )
    result['total_amount_won'] = clue['n']
    del result["_id"]
    return result
    # with psycopg.connect() as conn:
    #     with conn.cursor() as cur:
    #         cur.execute(
    #             f"""
    #             SELECT games.id, 
    #             games.episode_id, 
    #             games.aired, 
    #             games.canon,
    #                 COUNT(clues.*) AS total_amount_won
    #             FROM games
    #             LEFT OUTER JOIN clues
    #                 ON(clues.game_id = games.id)
    #             WHERE games.id = %s
    #             GROUP BY games.id

    #         """,
    #             [game_id],
    #         )
    #         row = cur.fetchone()
    #         if row is None:
    #             response.status_code = status.HTTP_404_NOT_FOUND
    #             return {"message": "Category not found"}
    #         record = {}
    #         for i, column in enumerate(cur.description):
    #             record[column.name] = row[i]
    #         return record

@router.post(
    "/api/custom-games",
    response_model=CustomGameOut,
    responses={409: {"model": Message}},
)
def create_custom_game():
    client = pymongo.MongoClient(mongo_str)
    db = client[dbname]
    with client.start_session() as session:
        with session.start_transaction():
            cat = db.game_definitions.insert_one({'created_on': datetime.utcnow()})
            return_cat = db.game_definitions.find_one({'_id': cat.inserted_id})
            return_cat['id'] = str(return_cat['_id'])
            clues = list(db.clues.aggregate([{"$match": {"canon": {"$eq": True}}},{"$sample": {"size": 30}}]))
            for clue in clues:
                clue['id'] = str(clue['_id'])
                category = db.categories.find_one({"_id": clue["category_id"]})
                db.categories.find()
                clue["category"] = category
                del clue["category_id"]
                db.game_definition_clues.insert_one({'game_definition_id': return_cat['_id'],'clue_id': clue['_id']})
                del clue['_id']
            return_cat['clues'] = clues
            del return_cat["_id"]
            return return_cat
#     with psycopg.connect() as conn:
#         with conn.cursor() as cur:
#             try:
#                 # Uses the RETURNING clause to get the data
#                 # just inserted into the database. See
#                 # https://www.postgresql.org/docs/current/sql-insert.html
                
#                 cur.execute(
#                 f"""
#                 SELECT clues.id, clues.answer, 
#                 clues.question, clues.value,
#                 clues.invalid_count, clues.category_id
#                 FROM clues
#                 WHERE clues.canon = true
#                 Limit 30;
#             """,
#             )

#                 clues = []
#                 for row in cur.fetchall():
#                     record = {}
#                     for i, column in enumerate(cur.description):
#                         record[column.name] = row[i]
#                     clues.append(record)
#                 cur.execute(
#                     f"""
#                     INSERT INTO game_definitions(created_on)
#                     VALUES (CURRENT_TIMESTAMP)
#                     RETURNING game_definitions.id;
#                     """
#                 )
#                 row = cur.fetchone()
#                 record = {}
#                 for i, column in enumerate(cur.description):
#                     record[column.name] = row[i]
#                 def_id = record

#                 for row in clues:
#                     cur.execute(
#                     f"""
#                     INSERT INTO game_defintion_clues(game_definition_id, clue_id)
#                     VALUES (%s, %s)
#                     """,
#                     [def_id, row["id"]],
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
@router.get(
    "/api/custom-games/{custom_game_id}",
    response_model=CustomGameOut,
    responses={404: {"model": Message}},
)
def get_custom_game(custom_game_id: Union[int, str]):
    client = pymongo.MongoClient(mongo_str)
    db = client[dbname]
    if isinstance(custom_game_id, str):
        true_id = bson.objectid.ObjectId(custom_game_id)
    else:
        true_id = custom_game_id
    result = db.game_definitions.find_one({"_id": true_id})
    result["id"] = str(result["_id"])
    game_defs = list(db.game_definition_clues.find({'game_definition_id': result['_id']}))
    clues = []
    for game_def in game_defs:
        c = db.clues.find_one({'_id': game_def['clue_id']})
        c['id'] = str(c['_id'])
        category = db.categories.find_one({"_id": c["category_id"]})
        del category['canon']
        c["category"] = category
        category['id'] = str(category["_id"])
        del c["canon"]
        del c["game_id"]
        del c["category_id"]
        del c['_id']
        clues.append(c)
    result['clues'] = clues
    del result["_id"]
    return result