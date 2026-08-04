import requests
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

create = """
CREATE TABLE IF NOT EXISTS train_numbers (
    id INTEGER PRIMARY KEY,
    train_no TEXT,
    station TEXT,
    query_time TEXT
);
"""

insert = "INSERT INTO train_numbers (train_no, station, query_time) VALUES (?, ?, ?)"

def get_arrivals(station):
    url = f"https://api.tfl.gov.uk/Line/district/Arrivals/940GZZLU{station}?direction=inbound"
    r = requests.get(url)
    r.raise_for_status()
    return r.json()

with sqlite3.connect(DATA / "tfl_train_data.db") as conn:
    cursor = conn.cursor()
    cursor.execute(create)
    for station in ["GTR", "HSK"]:
        try:
            arrivals = get_arrivals(station)
        except:
            continue
        t = datetime.now(timezone.utc)
        for train in arrivals:
            train_no = train["vehicleId"]
            cursor.execute(insert, train_no, station, t)
    cursor.commit()