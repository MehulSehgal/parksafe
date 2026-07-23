"""
Seeds backend-python/parksafe.db with the same Central Delhi demo spots
used by the frontend (index.html `spots` array), so the Python API and the
static demo UI show consistent data.

Usage:
    python3 scripts/seed_db.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend-python"))

import db  # noqa: E402

SEED_SPOTS = [
    dict(name="Connaught Place — Inner Circle", area="Connaught Place", lat=28.6315, lng=77.2167,
         price=40, spots_left=12, total=15, legal_status="Legal", cctv=True, lighting=True,
         patrolled=True, tow_zone=False, theft_reports=0, community_rating=4.6, reviews_count=132),
    dict(name="Janpath Market Lot", area="Janpath", lat=28.6270, lng=77.2190,
         price=30, spots_left=5, total=10, legal_status="Restricted", cctv=False, lighting=True,
         patrolled=False, tow_zone=True, theft_reports=6, community_rating=3.4, reviews_count=58),
    dict(name="Khan Market North Bay", area="Khan Market", lat=28.5992, lng=77.2265,
         price=60, spots_left=2, total=8, legal_status="Legal", cctv=True, lighting=True,
         patrolled=True, tow_zone=False, theft_reports=0, community_rating=4.8, reviews_count=210),
    dict(name="India Gate Lawns Parking", area="India Gate", lat=28.6129, lng=77.2295,
         price=0, spots_left=20, total=25, legal_status="Legal", cctv=False, lighting=True,
         patrolled=False, tow_zone=False, theft_reports=1, community_rating=4.1, reviews_count=96),
    dict(name="Barakhamba Road Basement", area="Barakhamba Road", lat=28.6285, lng=77.2225,
         price=50, spots_left=0, total=12, legal_status="Legal", cctv=True, lighting=False,
         patrolled=False, tow_zone=False, theft_reports=0, community_rating=4.4, reviews_count=74),
    dict(name="Sunder Nagar Driveway", area="Sunder Nagar", lat=28.6030, lng=77.2420,
         price=0, spots_left=8, total=8, legal_status="Illegal", cctv=False, lighting=False,
         patrolled=False, tow_zone=True, theft_reports=18, community_rating=2.3, reviews_count=19),
    dict(name="Gole Market Open Lot", area="Gole Market", lat=28.6360, lng=77.2010,
         price=20, spots_left=15, total=15, legal_status="Restricted", cctv=False, lighting=True,
         patrolled=False, tow_zone=False, theft_reports=3, community_rating=3.1, reviews_count=41),
]


def main():
    db.init_db()
    session = db.SessionLocal()
    try:
        if session.query(db.Spot).count() > 0:
            print("DB already seeded — skipping. Delete backend-python/parksafe.db to reseed.")
            return
        for s in SEED_SPOTS:
            session.add(db.Spot(**s))
        session.commit()
        print(f"Seeded {len(SEED_SPOTS)} spots into {db.DB_URL}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
