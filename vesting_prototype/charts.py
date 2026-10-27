"""Chart definitions for the app, written as plain Vega-Lite specs.

Streamlit draws these with st.vega_lite_chart, so nothing extra needs installing. Each function
returns (dataframe, spec). Colors are restrained: one accent for the active view, grey for the baseline.
"""
import pandas as pd

ACCENT, BASE_GREY = "#2563EB", "#8A94A6"
UP, DOWN, TOTAL = "#0D9488", "#EA580C", "#64748B"
SPLIT_PALETTE = ["#2563EB", "#0D9488", "#EA580C", "#7C3AED", "#CA8A04", "#DB2777", "#0891B2", "#65A30D", "#94A3B8"]
MONEY_AXIS = "$~s"


def short_money(x: float) -> str:
    """$13.3M, $850K, $420. Used for headlines and chart labels."""
    sign = "-" if x < 0 else ""
    x = abs(x)
    for div, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if x >= div:
            v = x / div
            return f"{sign}${v:.1f}{suffix}" if v < 100 else f"{sign}${v:.0f}{suffix}"
    return f"{sign}${x:,.0f}"


def short_num(x: float) -> str:
    sign = "-" if x < 0 else ""
    x = abs(x)
    for div, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if x >= div:
            v = x / div
            return f"{sign}{v:.1f}{suffix}" if v < 100 else f"{sign}{v:.0f}{suffix}"
    return f"{sign}{x:,.0f}"


_CONFIG = {"view": {"stroke": None}, "axis": {"grid": True, "gridOpacity": 0.25, "domain": False, "ticks": False,
           "labelFontSize": 11, "titleFontSize": 11}, "legend": {"orient": "top", "title": None, "labelFontSize": 12}}


def monthly_chart(series: pd.DataFrame, is_money: bool, compare: bool, height: int = 300):
    """series: index = month text like '2026-11', one column per line. compare=True means the columns
    are 'Current' and 'What-if' (drawn grey dashed and blue solid)."""
    long = series.reset_index().melt(id_vars="month", var_name="series", value_name="value")
    long["month"] = pd.to_datetime(long["month"] + "-01")
    fmt = MONEY_AXIS if is_money else "~s"
    names = list(series.columns)
    if compare:
        color = {"field": "series", "type": "nominal",
                 "scale": {"domain": ["Current", "What-if"], "range": [BASE_GREY, ACCENT]}}
        dash = {"field": "series", "type": "nominal", "legend": None,
                "scale": {"domain": ["Current", "What-if"], "range": [[5, 4], [1, 0]]}}
    else:
        color = {"field": "series", "type": "nominal",
                 "scale": {"domain": names, "range": SPLIT_PALETTE[:len(names)]},
                 **({"legend": None} if len(names) == 1 else {})}
        dash = {"value": [1, 0]}
    spec = {
        "height": height, "config": _CONFIG,
        "mark": {"type": "line", "strokeWidth": 2.5, "point": {"size": 40, "filled": True}, "interpolate": "monotone"},
        "encoding": {
            "x": {"field": "month", "type": "temporal", "timeUnit": "yearmonth",
                  "axis": {"title": None, "format": "%b %y", "labelAngle": 0, "labelOverlap": True, "grid": False}},
            "y": {"field": "value", "type": "quantitative", "axis": {"title": None, "format": fmt}},
            "color": color, "strokeDash": dash,
            "tooltip": [{"field": "month", "type": "temporal", "timeUnit": "yearmonth", "title": "Month",
                         "format": "%B %Y"},
                        {"field": "series", "type": "nominal", "title": "Line"},
                        {"field": "value", "type": "quantitative", "title": "Amount",
                         "format": "$,.0f" if is_money else ",.0f"}],
        },
    }
    return long, spec


def bridge_chart(steps: list[tuple[str, float]], height: int = 280):
    """steps: [(label, total_after_step)]. First is the current total, last the what-if total.
    Draws a waterfall: start bar, one floating bar per lever, end bar."""
    short = {"Current schedule": "Current", "People events": "People", "Attrition": "Attrition",
             "Share price change": "Price move", "Price path": "Price path"}
    rows, prev = [], None
    for i, (label, total) in enumerate(steps):
        name = short.get(label, label)
        if i == 0:
            rows.append({"label": name, "start": 0.0, "end": total, "kind": "Total", "text": short_money(total)})
        else:
            d = total - prev
            rows.append({"label": name, "start": prev, "end": total, "kind": "Increase" if d >= 0 else "Decrease",
                         "text": ("+" if d >= 0 else "-") + short_money(abs(d)).lstrip("-")})
        prev = total
    rows.append({"label": "What-if", "start": 0.0, "end": prev, "kind": "Total", "text": short_money(prev)})
    df = pd.DataFrame(rows)
    df["top"] = df[["start", "end"]].max(axis=1)
    x = {"field": "label", "type": "ordinal", "sort": None,
         "axis": {"title": None, "labelAngle": 0, "labelLimit": 90, "grid": False}}
    spec = {
        "height": height, "config": _CONFIG,
        "encoding": {"x": x},
        "layer": [
            {"mark": {"type": "bar", "size": 34, "cornerRadiusTopLeft": 3, "cornerRadiusTopRight": 3},
             "encoding": {
                 "y": {"field": "start", "type": "quantitative", "axis": {"title": None, "format": MONEY_AXIS}},
                 "y2": {"field": "end"},
                 "color": {"field": "kind", "type": "nominal", "legend": None,
                           "scale": {"domain": ["Total", "Increase", "Decrease"], "range": [TOTAL, UP, DOWN]}},
                 "tooltip": [{"field": "label", "title": "Step"},
                             {"field": "text", "title": "Amount"}]}},
            {"mark": {"type": "text", "baseline": "bottom", "dy": -4, "fontSize": 12, "fontWeight": 600},
             "encoding": {"y": {"field": "top", "type": "quantitative"}, "text": {"field": "text"}}},
        ],
    }
    return df, spec


def bullet_chart(names, shown, baseline=None, is_money: bool = True):
    """Horizontal bars of the active view. If baseline is given, a tick marks the current-schedule value."""
    df = pd.DataFrame({"name": list(names), "value": list(shown)})
    fmt_label = short_money if is_money else short_num
    df["label"] = df["value"].map(fmt_label)
    if baseline is not None:
        df["baseline"] = list(baseline)
    height = max(70, 30 * len(df) + 24)
    ytype = {"field": "name", "type": "nominal", "sort": None, "axis": {"title": None, "labelLimit": 150, "grid": False}}
    xaxis = {"title": None, "format": MONEY_AXIS if is_money else "~s"}
    layers = [
        {"mark": {"type": "bar", "color": ACCENT, "cornerRadiusEnd": 3, "size": 18},
         "encoding": {"y": ytype, "x": {"field": "value", "type": "quantitative", "axis": xaxis},
                      "tooltip": [{"field": "name", "title": "Name"},
                                  {"field": "value", "type": "quantitative", "title": "Value",
                                   "format": "$,.0f" if is_money else ",.0f"}]}},
        {"mark": {"type": "text", "align": "left", "dx": 5, "fontSize": 11},
         "encoding": {"y": ytype, "x": {"field": "value", "type": "quantitative"}, "text": {"field": "label"}}},
    ]
    if baseline is not None:
        layers.insert(1, {"mark": {"type": "tick", "color": BASE_GREY, "thickness": 3, "size": 24},
                          "encoding": {"y": ytype, "x": {"field": "baseline", "type": "quantitative"},
                                       "tooltip": [{"field": "baseline", "type": "quantitative", "title": "Current",
                                                    "format": "$,.0f" if is_money else ",.0f"}]}})
    return df, {"height": height, "config": _CONFIG, "layer": layers}
