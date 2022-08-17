from fastapi import APIRouter, Response, status
from pydantic import BaseModel
# from categories import CategoryOut
import psycopg

# Using routers for organization
# See https://fastapi.tiangolo.com/tutorial/bigger-applications/
router = APIRouter()


class ClueIn(BaseModel):
    id: int


class ClueOut(BaseModel):
    id: int
    answer: str
    question: str
    value: int
    invalid_count: int
    category: object
    canon: bool

class Clues(BaseModel):
    page_count: int
    categories: list[ClueOut]


class Message(BaseModel):
    message: str


@router.get("/api/clues", response_model=Clues)
def clues_list(page: int = 0):
    # Uses the environment variables to connect
    # In development, see the docker-compose.yml file for
    #   the PG settings in the "environment" section
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT clues.id, 
                clues.answer, 
                clues.question, 
                clues.value, 
                clues.invalid_count,
                clues.canon,
                clues.category_id AS category,
                categories.id AS id,
                categories.title, 
                categories.canon AS canon
                FROM categories
                JOIN clues
                    ON (categories.id = clues.category_id)
                WHERE clues.invalid_count = 0
                LIMIT 100 OFFSET %s
            """,
                [page * 100],
            )

            results = []
            for row in cur.fetchall():
                record = {}
                grouping = False
                category_object = {}
                for i, column in enumerate(cur.description):
                    if grouping == False:
                        record[column.name] = row[i]
                    else:
                        category_object[column.name] = row[i]
                    if column.name == "category":
                        grouping = True
                record["category"] = category_object
                results.append(record)

            cur.execute(
                """
                SELECT COUNT(*) FROM clues;
            """
            )
            raw_count = cur.fetchone()[0]
            page_count = (raw_count // 100) + 1

            return Clues(page_count=page_count, categories=results)


@router.get(
    "/api/clues/{clue_id}",
    response_model=ClueOut,
    responses={404: {"model": Message}},
)
def get_clue(clue_id: int, response: Response):
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT clues.id, 
                clues.answer, 
                clues.question, 
                clues.value, 
                clues.invalid_count,
                clues.canon,
                clues.category_id AS category,
                categories.id AS id,
                categories.title, 
                categories.canon AS canon
                FROM categories
                JOIN clues
                    ON (categories.id = clues.category_id)
                WHERE clues.id = %s AND clues.invalid_count = 0;
            """,
                [clue_id],
            )
            row = cur.fetchone()
            if row is None:
                response.status_code = status.HTTP_404_NOT_FOUND
                return {"message": "Clue not found"}
            record = {}
            grouping = False
            category_object = {}
            for i, column in enumerate(cur.description):
                if grouping == False:
                    record[column.name] = row[i]
                else:
                    category_object[column.name] = row[i]
                if column.name == "category":
                    grouping = True
            record["category"] = category_object
            return record

@router.get(
    "/api/random-clue",
    response_model=ClueOut,
    responses={404: {"model": Message}},
)
def get_random_clue(response: Response, valid: bool = True):
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            if valid == True:
                cur.execute(
                    f"""
                    SELECT clues.id, 
                    clues.answer, 
                    clues.question, 
                    clues.value, 
                    clues.invalid_count,
                    clues.canon,
                    clues.category_id AS category,
                    categories.id AS id,
                    categories.title, 
                    categories.canon AS canon
                    FROM categories
                    JOIN clues
                        ON (categories.id = clues.category_id)
                    WHERE clues.invalid_count = 0
                    ORDER BY RANDOM() LIMIT 1;
                """,
                    [],
                )
            else:
                cur.execute(
                    f"""
                    SELECT clues.id, 
                    clues.answer, 
                    clues.question, 
                    clues.value, 
                    clues.invalid_count,
                    clues.canon,
                    clues.category_id AS category,
                    categories.id AS id,
                    categories.title, 
                    categories.canon AS canon
                    FROM categories
                    JOIN clues
                        ON (categories.id = clues.category_id)
                    ORDER BY RANDOM() LIMIT 1;
                """,
                    [],
                )
            row = cur.fetchone()
            if row is None:
                response.status_code = status.HTTP_404_NOT_FOUND
                return {"message": "Clue not found"}
            record = {}
            grouping = False
            category_object = {}
            for i, column in enumerate(cur.description):
                if grouping == False:
                    record[column.name] = row[i]
                else:
                    category_object[column.name] = row[i]
                if column.name == "category":
                    grouping = True
            record["category"] = category_object
            return record
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
def remove_clue(clue_id: int, response: Response):
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    f"""
                    UPDATE clues
                    SET invalid_count = invalid_count + 1

                    WHERE id = %s;
                """,
                    [clue_id],
                )
                return get_clue(clue_id, response)
            except psycopg.errors.ForeignKeyViolation:
                response.status_code = status.HTTP_404_BAD_REQUEST
                return {
                    "message": "Cannot delete clue",
                }
