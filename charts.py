import anthropic
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
import pandas as pd
import base64
import io
import json

client = anthropic.Anthropic()

PALETTE = ['#97ce4c', '#00b0c8', '#e4a116', '#c73232', '#9b59b6', '#44c4a1', '#ff9500', '#e0e0e0']
BG      = '#1a1a1a'
FG      = '#cccccc'
GRID    = '#2a2a2a'


def _apply_dark_theme(fig, ax):
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.tick_params(colors=FG, labelsize=11)
    ax.xaxis.label.set_color(FG)
    ax.yaxis.label.set_color(FG)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


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
    mpl.rcParams['font.family'] = 'sans-serif'

    fig, ax = plt.subplots(figsize=(10, 6))
    _apply_dark_theme(fig, ax)

    x   = chart_info.get("x") or None
    y   = chart_info.get("y") or None
    hue = chart_info.get("hue") or None

    kwargs = {"data": df, "ax": ax}
    if x:   kwargs["x"] = x
    if y:   kwargs["y"] = y
    if hue: kwargs["hue"] = hue

    chart = chart_info.get("chart", "barplot")

    if chart in ("barplot", "countplot", "boxplot"):
        kwargs["palette"] = PALETTE
    elif chart in ("histplot", "lineplot", "scatterplot"):
        kwargs["color"] = PALETTE[0]

    getattr(sns, chart)(**kwargs)

    ax.set_title("")
    ax.set_xlabel(ax.get_xlabel(), color=FG)
    ax.set_ylabel(ax.get_ylabel(), color=FG)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()
