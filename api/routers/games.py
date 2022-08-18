from fastapi import APIRouter, Response, status
from pydantic import BaseModel
# from categories import CategoryOut
import psycopg
from routers.clues import ClueOut

# Using routers for organization
# See https://fastapi.tiangolo.com/tutorial/bigger-applications/
router = APIRouter()

class GameIn(BaseModel):
    id: int

class GameOut(BaseModel):
    id: int
    episode_id: int
    aired: str
    canon: bool
    total_amount_won: int

class CustomGameIn(BaseModel):
    id: int
    created_on: str

class CustomGameOut(BaseModel):
    id: int
    created_on: str
    clues: ClueOut

class Message(BaseModel):
    message: str

class Games(BaseModel):
    games: list[GameOut]


@router.get(
    "/api/games/{game_id}",
    response_model=GameOut,
    responses={404: {"model": Message}},)
def get_game(game_id: int, response: Response):
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT games.id, 
                games.episode_id, 
                games.aired, 
                games.canon,
                    COUNT(clues.*) AS total_amount_won
                FROM games
                LEFT OUTER JOIN clues
                    ON(clues.game_id = games.id)
                WHERE games.id = %s
                GROUP BY games.id

            """,
                [game_id],
            )
            row = cur.fetchone()
            if row is None:
                response.status_code = status.HTTP_404_NOT_FOUND
                return {"message": "Category not found"}
            record = {}
            for i, column in enumerate(cur.description):
                record[column.name] = row[i]
            return record

@router.post(
    "/api/custom-games",
    response_model=CustomGameOut,
    responses={409: {"model": Message}},
)
def create_custom_game(category: CustomGameIn, response: Response):
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            try:
                # Uses the RETURNING clause to get the data
                # just inserted into the database. See
                # https://www.postgresql.org/docs/current/sql-insert.html
                
                cur.execute(
                f"""
                SELECT clues.id, clues.answer, 
                clues.question, clues.value,
                clues.invalid_count, clues.category_id
                FROM clues
                WHERE clues.canon = true
                Limit 30

            """,
            )

                cur.execute(
                    """
                    INSERT INTO categories (title, canon)
                    VALUES (%s, false)
                    RETURNING id, title, canon;
                """,
                    [category.title],
                )
            except psycopg.errors.UniqueViolation:
                # status values at https://github.com/encode/starlette/blob/master/starlette/status.py
                response.status_code = status.HTTP_409_CONFLICT
                return {
                    "message": "Could not create duplicate category",
                }
            row = cur.fetchone()
            record = {}
            for i, column in enumerate(cur.description):
                record[column.name] = row[i]
            return record
