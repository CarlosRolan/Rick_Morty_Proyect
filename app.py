from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import anthropic
from sqlalchemy import create_engine, text
import pandas as pd
import json
import os
from charts import choose_chart, generate_chart

load_dotenv()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
client = anthropic.Anthropic()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# Database schema — must match the tables defined in proyect_flow.ipynb
SCHEMA = """
TABLE locations (
    id INTEGER PRIMARY KEY,
    name VARCHAR,
    type VARCHAR,
    dimension VARCHAR
);

TABLE characters (
    id INTEGER PRIMARY KEY,
    name VARCHAR,
    status VARCHAR,
    species VARCHAR,
    type VARCHAR,
    gender VARCHAR,
    location_id INTEGER REFERENCES locations(id)
);

TABLE episodes (
    id INTEGER PRIMARY KEY,
    name VARCHAR,
    air_date VARCHAR,
    episode VARCHAR
);

TABLE character_episode (
    character_id INTEGER REFERENCES characters(id),
    episode_id INTEGER REFERENCES episodes(id)
);
"""


def run_query(sql: str) -> pd.DataFrame:
    # Executes a SELECT query against the database and returns the result as a DataFrame
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


def question_to_sql(question: str) -> str:
    # Sends the user's natural language question to Claude and returns a SQL SELECT query.
    # If the question could modify the database, Claude returns QUESTION_ERROR instead.
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        system=[{
            "type": "text",
            "text": f"""You are a SQL expert. Transform the user's question into a valid PostgreSQL SELECT query.
Return ONLY the SQL query, with no explanations, markdown or code blocks.
Only generate SELECT statements — queries that modify the database are not allowed.
If the question could modify the database, return the code QUESTION_ERROR instead.

{SCHEMA}""",
            "cache_control": {"type": "ephemeral"}
        }],
        messages=[{"role": "user", "content": question}]
    )
    return response.content[0].text.strip()


@app.get("/stats/locations")
async def stats_locations():
    df = run_query("""
        SELECT l.name, COUNT(c.id) AS count
        FROM locations l
        JOIN characters c ON c.location_id = l.id
        GROUP BY l.name
        ORDER BY count DESC
        LIMIT 8
    """)
    return {"labels": df["name"].tolist(), "values": df["count"].tolist()}


@app.get("/stats/species")
async def stats_species():
    df = run_query("""
        SELECT species, COUNT(*) AS count
        FROM characters
        GROUP BY species
        ORDER BY count DESC
        LIMIT 8
    """)
    return {"labels": df["species"].tolist(), "values": df["count"].tolist()}


class Question(BaseModel):
    question: str


@app.post("/ask")
async def ask(body: Question):
    # Main endpoint: receives a natural language question, generates SQL via Claude,
    # queries the database, picks the best chart and returns it as base64.
    try:
        print(f"[1] Question received: {body.question}")
        sql = question_to_sql(body.question)
        print(f"[2] Generated SQL: {sql}")

        if sql == "QUESTION_ERROR":
            return {"status": "error", "message": "The question is not valid for querying the database."}

        print(f"[3] Running query...")
        df = run_query(sql)
        print(f"[4] Rows returned: {len(df)}, columns: {list(df.columns)}")

        print(f"[5] Choosing chart...")
        chart_info = choose_chart(df)
        print(f"[6] Chart selected: {chart_info}")

        print(f"[7] Generating chart...")
        chart_b64 = generate_chart(df, chart_info)
        print(f"[8] Chart generated OK, size: {len(chart_b64)} bytes")
        return {"status": "ok", "chart": chart_b64}

    except Exception as e:
        import traceback
        print(f"[ERROR] {e}")
        print(traceback.format_exc())
        if "credit balance is too low" in str(e):
            return {"status": "no_credits"}
        return {"status": "server_error"}