"""
ParkSafe analytics report (Python / pandas).

Pulls spots from the SQLite DB and challans from the Java municipal service,
and produces a self-contained HTML report municipal admins can glance at —
top tow-risk areas, safety-score distribution, and outstanding challan value.

Usage:
    # with backend-python/app.py and service-java/ChallanService running:
    python3 scripts/generate_report.py

Produces:
    reports/parking_report.html
"""
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend-python"))

import db  # noqa: E402

try:
    import java_bridge  # noqa: E402
    HAVE_JAVA_BRIDGE = True
except ImportError:
    HAVE_JAVA_BRIDGE = False

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.normpath(os.path.join(HERE, "..", "reports", "parking_report.html"))


def load_spots_df() -> pd.DataFrame:
    session = db.SessionLocal()
    try:
        rows = session.query(db.Spot).all()
        return pd.DataFrame([{
            "id": r.id, "name": r.name, "area": r.area, "legal_status": r.legal_status,
            "safety_score": r.safety_score, "tow_zone": r.tow_zone,
            "theft_reports": r.theft_reports, "community_rating": r.community_rating,
            "reviews_count": r.reviews_count,
        } for r in rows])
    finally:
        session.close()


def load_challans_df() -> pd.DataFrame:
    if not HAVE_JAVA_BRIDGE:
        return pd.DataFrame()
    try:
        challans = java_bridge.list_challans()
    except Exception:
        return pd.DataFrame()
    return pd.DataFrame(challans)


def build_report(spots: pd.DataFrame, challans: pd.DataFrame) -> str:
    if spots.empty:
        return "<h1>ParkSafe Report</h1><p>No spot data found — run scripts/seed_db.py first.</p>"

    by_area = (
        spots.groupby("area")
        .agg(avg_safety=("safety_score", "mean"), tow_zones=("tow_zone", "sum"),
             theft_reports=("theft_reports", "sum"), spots=("id", "count"))
        .sort_values("avg_safety")
        .round(1)
    )

    risk_zone_count = int((spots["safety_score"] < 50).sum())
    green_zone_count = int(((spots["safety_score"] >= 80) & (spots["legal_status"] == "Legal")).sum())

    challan_summary_html = "<p><em>Municipal service (Java) not reachable — run service-java/ChallanService for challan stats.</em></p>"
    if not challans.empty:
        total_amount = challans["amount"].sum()
        unpaid = challans[challans["status"] == "UNPAID"]["amount"].sum()
        challan_summary_html = f"""
        <table>
          <tr><th>Total challans issued</th><td>{len(challans)}</td></tr>
          <tr><th>Total value</th><td>₹{total_amount:,.0f}</td></tr>
          <tr><th>Outstanding (unpaid)</th><td>₹{unpaid:,.0f}</td></tr>
        </table>
        {challans[["id", "area", "plate", "amount", "reason", "status"]].to_html(index=False)}
        """

    return f"""
    <html>
    <head>
      <meta charset="utf-8">
      <title>ParkSafe Municipal Report</title>
      <style>
        body {{ font-family: -apple-system, Arial, sans-serif; margin: 40px; color: #1a1a2e; background: #fafafa; }}
        h1 {{ color: #6c3ce0; }}
        h2 {{ border-bottom: 2px solid #eee; padding-bottom: 6px; }}
        table {{ border-collapse: collapse; margin: 12px 0; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
        th {{ background: #f0ecff; }}
        .stat {{ display: inline-block; margin-right: 30px; font-size: 15px; }}
        .stat b {{ font-size: 22px; display: block; color: #6c3ce0; }}
      </style>
    </head>
    <body>
      <h1>ParkSafe Municipal Report</h1>
      <p>Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

      <div class="stat"><b>{len(spots)}</b>Total spots tracked</div>
      <div class="stat"><b>{risk_zone_count}</b>Spots below safety 50</div>
      <div class="stat"><b>{green_zone_count}</b>Green Zone spots</div>

      <h2>Safety by area (lowest first — attention needed)</h2>
      {by_area.to_html()}

      <h2>Challans (Java municipal service)</h2>
      {challan_summary_html}
    </body>
    </html>
    """


def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    spots = load_spots_df()
    challans = load_challans_df()
    html = build_report(spots, challans)
    with open(OUT_PATH, "w") as f:
        f.write(html)
    print(f"Report written -> {OUT_PATH}")


if __name__ == "__main__":
    main()
