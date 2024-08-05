import os

from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv()

postgres_url = URL.create(
    "postgresql+asyncpg",
    username=os.getenv("POSTGRES_USER"),
    host=os.getenv("POSTGRES_HOST"),
    database=os.getenv("POSTGRES_DB"),
    port=os.getenv("POSTGRES_PORT"),
    password=os.getenv("POSTGRES_PASSWORD"),
)
