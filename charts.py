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
MAX_BARS = 15


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
        system="""You are a data visualization expert using seaborn and matplotlib.
Given the schema and a sample of a DataFrame, decide which chart type fits best.
Rules:
- Use "pie" when showing proportions of a whole (species, gender, status distributions). Ideal when there are few categories (under 8).
- Use "barplot" for comparing a numeric value across categories.
- Use "countplot" for counting occurrences of a categorical variable.
- Use "lineplot" for time series or ordered sequences.
- Use "scatterplot" for correlations between two numeric variables.
- Use "histplot" for distributions of a single numeric variable.
- Use "boxplot" for statistical distributions across groups.
Return ONLY a valid JSON with this exact format:
{"chart": "barplot|countplot|lineplot|scatterplot|histplot|boxplot|pie", "x": "column_or_null", "y": "column_or_null", "hue": "column_or_null"}""",
        messages=[{"role": "user", "content": json.dumps(info, default=str)}]
    )
    return json.loads(response.content[0].text.strip())


def generate_chart(df: pd.DataFrame, chart_info: dict) -> str:
    mpl.rcParams['font.family'] = 'sans-serif'

    chart = chart_info.get("chart", "barplot")
    x_col = chart_info.get("x") or None
    y_col = chart_info.get("y") or None
    hue   = chart_info.get("hue") or None

    # Limit rows for bar-type charts to avoid overcrowding
    if chart in ("barplot", "countplot") and len(df) > MAX_BARS:
        df = df.head(MAX_BARS)

    fig, ax = plt.subplots(figsize=(10, 6))
    _apply_dark_theme(fig, ax)

    if chart == "pie":
        # Determine labels and values
        if x_col and y_col:
            labels = df[x_col].astype(str).tolist()
            values = df[y_col].tolist()
        elif x_col:
            counts = df[x_col].value_counts().head(MAX_BARS)
            labels = counts.index.astype(str).tolist()
            values = counts.values.tolist()
        else:
            labels = df.iloc[:, 0].astype(str).tolist()
            values = df.iloc[:, 1].tolist()

        colors = PALETTE[:len(labels)]
        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            colors=colors,
            autopct='%1.1f%%',
            pctdistance=0.82,
            startangle=90,
            wedgeprops={'edgecolor': BG, 'linewidth': 2}
        )
        for t in texts:
            t.set_color(FG)
            t.set_fontsize(10)
        for t in autotexts:
            t.set_color(BG)
            t.set_fontsize(9)
            t.set_fontweight('bold')
        ax.set_aspect('equal')

    else:
        kwargs = {"data": df, "ax": ax}
        if x_col: kwargs["x"] = x_col
        if y_col: kwargs["y"] = y_col
        if hue:   kwargs["hue"] = hue

        if chart in ("barplot", "countplot", "boxplot"):
            kwargs["palette"] = PALETTE
        elif chart in ("histplot", "lineplot", "scatterplot"):
            kwargs["color"] = PALETTE[0]

        getattr(sns, chart)(**kwargs)

        ax.set_xlabel(ax.get_xlabel(), color=FG)
        ax.set_ylabel(ax.get_ylabel(), color=FG)

        # Rotate x labels to avoid overlap
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right', fontsize=10)

    ax.set_title("")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()
