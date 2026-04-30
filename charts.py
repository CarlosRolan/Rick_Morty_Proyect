import anthropic
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import base64
import io
import json

client = anthropic.Anthropic()


def choose_chart(df: pd.DataFrame) -> dict:
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
