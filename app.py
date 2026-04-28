from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import anthropic
from sqlalchemy import create_engine, text
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import base64
import io
import json
import os

app = FastAPI()
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


def choose_chart(df: pd.DataFrame) -> dict:
    # Sends the DataFrame structure and a sample to Claude, which decides
    # the most suitable seaborn chart type and the columns to use.
    info = {
        "columns": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "rows": len(df),
        "sample": df.head(3).to_dict(orient="records")
    }
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=256,
        system="""You are a data visualization expert using seaborn.
Given the schema and a sample of a DataFrame, decide which chart type fits best.
Return ONLY a valid JSON with this exact format:
{"chart": "barplot|countplot|lineplot|scatterplot|histplot|boxplot", "x": "column_or_null", "y": "column_or_null", "hue": "column_or_null"}""",
        messages=[{"role": "user", "content": json.dumps(info, default=str)}]
    )
    return json.loads(response.content[0].text.strip())


def generate_chart(df: pd.DataFrame, chart_info: dict) -> str:
    # Generates a seaborn chart from the DataFrame using the chart type chosen by Claude.
    # Returns the chart as a base64-encoded PNG string.
    fig, ax = plt.subplots(figsize=(10, 6))

    x   = chart_info.get("x") or None
    y   = chart_info.get("y") or None
    hue = chart_info.get("hue") or None

    kwargs = {"data": df, "ax": ax}
    if x:   kwargs["x"] = x
    if y:   kwargs["y"] = y
    if hue: kwargs["hue"] = hue

    chart = chart_info.get("chart", "barplot")
    getattr(sns, chart)(**kwargs)

    ax.set_title("")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


class Question(BaseModel):
    question: str


@app.post("/ask")
async def ask(body: Question):
    # Main endpoint: receives a natural language question, generates SQL via Claude,
    # queries the database, picks the best chart and returns it as base64.
    sql = question_to_sql(body.question)
    print(f"Question: {body.question}")
    print(f"Generated SQL: {sql}")

    if sql == "QUESTION_ERROR":
        return {"status": "error", "message": "The question is not valid for querying the database."}

    df = run_query(sql)
    print(f"Rows returned: {len(df)}")

    chart_info = choose_chart(df)
    print(f"Chart selected: {chart_info}")

    chart_b64 = generate_chart(df, chart_info)
    return {"status": "ok", "chart": chart_b64}