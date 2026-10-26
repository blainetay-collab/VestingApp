"""Client-ready report builders (Excel and PDF) for the vesting tracker prototype."""
from __future__ import annotations

import io

import pandas as pd

DISCLAIMER = (
    "Estimated prices and values are illustrative projections based on the assumptions listed in this "
    "report. They are not forecasts, guarantees or investment advice. Share counts are gross, before any "
    "tax withholding or sell-to-cover, which varies by country. This report is not tax or legal advice."
)

DETAIL_COLUMNS = {
    "vest_date": "Vest date", "company": "Company", "employee_id": "Employee ID", "full_name": "Employee", "country": "Country",
    "grant_id": "Grant", "award_type": "Award", "shares_vesting": "Shares",
    "est_price_usd": "Est. price (USD)", "est_value_usd": "Est. value (USD)",
    "est_value_low": "Low (USD)", "est_value_high": "High (USD)",
    "local_currency": "Local ccy", "est_value_local": "Est. value (local)", "flags": "Review flags",
}


def _detail(events: pd.DataFrame, show_names: bool, scenario: str) -> pd.DataFrame:
    cols = list(DETAIL_COLUMNS)
    if not show_names:
        cols.remove("full_name")
    if scenario != "Range (bear / base / bull)":
        cols = [c for c in cols if c not in ("est_value_low", "est_value_high")]
    df = events[cols].copy()
    df["vest_date"] = df["vest_date"].dt.strftime("%Y-%m-%d")
    return df.rename(columns=DETAIL_COLUMNS)


def assumptions_table(meta: dict) -> pd.DataFrame:
    rows = [
        ("Company / ticker", meta.get("company", "")),
        ("Report date", meta["report_date"]),
        ("Data as of (price date)", meta["price_date"]),
        ("Window", meta["window"]),
        ("Starting share price (USD)", meta.get("price_text") or f"{meta['price']:,.2f}"),
        ("Price scenario", meta["scenario"]),
        ("Annual growth assumption", meta["growth_text"] if meta["scenario"] != "Flat" else "n/a"),
        ("Annual volatility assumption", meta["vol_text"] if meta["scenario"].startswith("Range") else "n/a"),
        ("Reporting currency", "USD; local currency shown using the FX rates in the data (illustrative)"),
        ("Filters applied", meta.get("filters") or "None"),
        ("View", meta.get("view", "Current schedule")),
    ]
    if meta.get("levers"):
        rows.append(("What-if assumptions", meta["levers"]))
    if meta.get("data_note"):
        rows.append(("Data note", meta["data_note"]))
    return pd.DataFrame(rows, columns=["Assumption", "Value"])


# --------------------------------------------------------------------------
# Excel
# --------------------------------------------------------------------------
def build_excel(events: pd.DataFrame, summaries: dict, meta: dict,
                include_detail: bool = True, show_names: bool = True) -> bytes:
    buf = io.BytesIO()
    month = summaries["by_month"].rename(columns={
        "month": "Month", "events": "Events", "shares": "Shares", "est_value_usd": "Est. value (USD)",
        "est_value_low": "Low (USD)", "est_value_high": "High (USD)"})
    country = summaries["by_country"].rename(columns={
        "country": "Country", "events": "Events", "shares": "Shares", "est_value_usd": "Est. value (USD)",
        "est_value_low": "Low (USD)", "est_value_high": "High (USD)"})
    company = summaries["by_company"].rename(columns={
        "company": "Company", "events": "Events", "shares": "Shares", "est_value_usd": "Est. value (USD)",
        "est_value_low": "Low (USD)", "est_value_high": "High (USD)"})
    if meta["scenario"] != "Range (bear / base / bull)":
        month = month.drop(columns=["Low (USD)", "High (USD)"], errors="ignore")
        country = country.drop(columns=["Low (USD)", "High (USD)"], errors="ignore")
        company = company.drop(columns=["Low (USD)", "High (USD)"], errors="ignore")
    sheets = [("By Month", month)]
    if events["company"].nunique() > 1:
        sheets.append(("By Company", company))
    sheets.append(("By Country", country))

    with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
        wb = xw.book
        hdr = wb.add_format({"bold": True, "bg_color": "#D9E1F2", "border": 1, "font_name": "Arial", "font_size": 10})
        base = wb.add_format({"font_name": "Arial", "font_size": 10})
        title = wb.add_format({"bold": True, "font_name": "Arial", "font_size": 14})
        bold = wb.add_format({"bold": True, "font_name": "Arial", "font_size": 10})
        money = wb.add_format({"num_format": "$#,##0", "font_name": "Arial", "font_size": 10})
        num = wb.add_format({"num_format": "#,##0", "font_name": "Arial", "font_size": 10})
        wrap = wb.add_format({"text_wrap": True, "font_name": "Arial", "font_size": 10, "valign": "top"})

        # Summary sheet
        ws = wb.add_worksheet("Summary")
        xw.sheets["Summary"] = ws
        ws.write(0, 0, f"Upcoming Vesting Events - {meta.get('company', '')}", title)
        ws.write(1, 0, f"Report date {meta['report_date']} | {meta['window']} | Scenario: {meta['scenario']} | "
                       f"{meta.get('view', 'Current schedule')}", base)
        ws.write(3, 0, "Events", bold); ws.write_number(3, 1, len(events), num)
        ws.write(4, 0, "Shares vesting", bold); ws.write_number(4, 1, float(events["shares_vesting"].sum()), num)
        ws.write(5, 0, "Estimated value (USD)", bold); ws.write_number(5, 1, float(events["est_value_usd"].sum()), money)
        if meta["scenario"].startswith("Range"):
            ws.write(6, 0, "Low / High (USD)", bold)
            ws.write(6, 1, f"${events['est_value_low'].sum():,.0f} / ${events['est_value_high'].sum():,.0f}", base)
        ws.write(8, 0, DISCLAIMER, wrap)
        ws.set_row(8, 75)
        ws.set_column(0, 0, 28, base); ws.set_column(1, 1, 22, base)

        for name, df in sheets:
            df.to_excel(xw, sheet_name=name, index=False)
            s = xw.sheets[name]
            for i, c in enumerate(df.columns):
                s.write(0, i, c, hdr)
                s.set_column(i, i, 18, money if "USD" in c else (num if c in ("Events", "Shares") else base))
            s.freeze_panes(1, 0)

        if include_detail:
            det = _detail(events, show_names, meta["scenario"])
            det.to_excel(xw, sheet_name="Events", index=False)
            s = xw.sheets["Events"]
            for i, c in enumerate(det.columns):
                s.write(0, i, c, hdr)
                fmt = money if "USD" in c or "local" in c else (num if c == "Shares" else base)
                s.set_column(i, i, 40 if c == "Review flags" else 16, fmt)
            s.freeze_panes(1, 0)
            s.autofilter(0, 0, len(det), len(det.columns) - 1)

        a = assumptions_table(meta)
        a.to_excel(xw, sheet_name="Assumptions", index=False)
        s = xw.sheets["Assumptions"]
        for i, c in enumerate(a.columns):
            s.write(0, i, c, hdr)
        s.set_column(0, 0, 30, base); s.set_column(1, 1, 90, wrap)
    return buf.getvalue()


# --------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------
def build_pdf(events: pd.DataFrame, summaries: dict, meta: dict,
              include_detail: bool = True, show_names: bool = True) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    small = styles["BodyText"].clone("small", fontSize=8, leading=10)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(letter), leftMargin=0.5 * inch, rightMargin=0.5 * inch,
                            topMargin=0.5 * inch, bottomMargin=0.5 * inch,
                            title=f"Upcoming Vesting Events - {meta.get('company', '')}")

    def table(df: pd.DataFrame, widths=None, font=8):
        data = [list(df.columns)] + df.astype(str).values.tolist()
        t = Table(data, repeatRows=1, colWidths=widths)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E1F2")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), font),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F7F7")]),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ]))
        return t

    def fmt_summary(df: pd.DataFrame, key: str, label: str) -> pd.DataFrame:
        out = pd.DataFrame({label: df[key], "Events": df["events"], "Shares": df["shares"].map("{:,.0f}".format),
                            "Est. value (USD)": df["est_value_usd"].map("${:,.0f}".format)})
        if meta["scenario"].startswith("Range"):
            out["Low (USD)"] = df["est_value_low"].map("${:,.0f}".format)
            out["High (USD)"] = df["est_value_high"].map("${:,.0f}".format)
        return out

    el = [Paragraph(f"Upcoming Vesting Events - {meta.get('company', '')}", styles["Title"]),
          Paragraph(f"Report date {meta['report_date']} &nbsp;|&nbsp; {meta['window']} &nbsp;|&nbsp; "
                    f"Scenario: {meta['scenario']} &nbsp;|&nbsp; {meta.get('view', 'Current schedule')}",
                    styles["BodyText"]), Spacer(1, 8)]

    kpi = [["Events", "Shares vesting", "Estimated value (USD)"],
           [f"{len(events):,}", f"{events['shares_vesting'].sum():,.0f}", f"${events['est_value_usd'].sum():,.0f}"]]
    if meta["scenario"].startswith("Range"):
        kpi[0].append("Low - High (USD)")
        kpi[1].append(f"${events['est_value_low'].sum():,.0f} - ${events['est_value_high'].sum():,.0f}")
    kt = Table(kpi)
    kt.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 10),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    el += [kt, Spacer(1, 10)]

    if not events.empty:
        el += [Paragraph("By month", styles["Heading3"]),
               table(fmt_summary(summaries["by_month"], "month", "Month")), Spacer(1, 8),
               *([Paragraph("By company", styles["Heading3"]),
                  table(fmt_summary(summaries["by_company"], "company", "Company")), Spacer(1, 8)]
                 if events["company"].nunique() > 1 else []),
               Paragraph("By country", styles["Heading3"]),
               table(fmt_summary(summaries["by_country"], "country", "Country")), Spacer(1, 8)]
        if include_detail:
            det = _detail(events, show_names, meta["scenario"])
            for c in det.columns:
                if "USD" in c or "local" in c:
                    det[c] = det[c].map("{:,.0f}".format) if "price" not in c else det[c].map("{:,.2f}".format)
                elif c == "Shares":
                    det[c] = det[c].map("{:,.0f}".format)
            det = det.drop(columns=["Review flags"], errors="ignore")
            el += [Paragraph("Event detail", styles["Heading3"]), table(det, font=7), Spacer(1, 8)]
    else:
        el.append(Paragraph("No vesting events in this window.", styles["BodyText"]))

    a = assumptions_table(meta)
    el += [Paragraph("Assumptions", styles["Heading3"]),
           table(a, widths=[2.2 * inch, 7.6 * inch]), Spacer(1, 8), Paragraph(DISCLAIMER, small)]
    doc.build(el)
    return buf.getvalue()


# --------------------------------------------------------------------------
# Raw data export (whatever the filters currently show)
# --------------------------------------------------------------------------
def build_data_workbook(events: pd.DataFrame, filters_text: str, meta: dict) -> bytes:
    """Excel file with the filtered events table plus a sheet describing the filters/assumptions."""
    buf = io.BytesIO()
    out = events.copy()
    out["vest_date"] = out["vest_date"].dt.strftime("%Y-%m-%d")
    with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
        hdr = xw.book.add_format({"bold": True, "bg_color": "#D9E1F2", "border": 1})
        out.to_excel(xw, sheet_name="Events", index=False)
        ws = xw.sheets["Events"]
        for i, c in enumerate(out.columns):
            ws.write(0, i, c, hdr)
            ws.set_column(i, i, 40 if c == "flags" else (22 if c in ("company", "full_name") else 15))
        ws.freeze_panes(1, 0)
        ws.autofilter(0, 0, len(out), len(out.columns) - 1)
        a = assumptions_table({**meta, "filters": filters_text})
        a.to_excel(xw, sheet_name="Filters and assumptions", index=False)
        ws2 = xw.sheets["Filters and assumptions"]
        ws2.set_column(0, 0, 30); ws2.set_column(1, 1, 90)
    return buf.getvalue()
