# What if historical data was collected and stored? This would give a better estimate of average wait time than any snapshot in time.
# Powered by Tfl Open Data

import sqlite3
import requests
from datetime import datetime, timezone

def find_arrivals(line, stopPointId):
    """find arrivals at a given station"""
    url=f"https://api.tfl.gov.uk/Line/{line}/Arrivals/{stopPointId}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()

def get_station_code(code: str):
    return "940GZZLU" + code

with sqlite3.connect("tfl_train_data.db") as conn:
    cursor = conn.cursor()
    create = """ 
    CREATE TABLE IF NOT EXISTS arrivals (
        id INTEGER PRIMARY KEY,
        station TEXT,
        query_time TEXT,
        arrival_time TEXT,
        time_to_station INTEGER,
        direction TEXT,
        destination TEXT,
        location TEXT
    );   
    """

    trainquery = """
    INSERT INTO arrivals (
        station, 
        query_time, 
        arrival_time, 
        time_to_station,
        direction,
        destination,
        location
    ) 
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """

    # create table if it doesn't exist
    cursor.execute(create)

    # insert values
    for station in ["WIP", "SFS", "EPY", "PYB", "PSG", "FBY"]:
        try:
            arrivals = find_arrivals("district", get_station_code(station))
        except requests.RequestException:
            print("Couldn't fetch")
            continue
        if not arrivals:
            cursor.execute(trainquery, (station, datetime.now(timezone.utc), None, None, None, None, None))
            continue
        for train in arrivals:
            values = (station, train.get("timestamp"), train.get("expectedArrival"), train.get("timeToStation"), train.get("direction"), train.get("towards"), train.get("currentLocation"))
            cursor.execute(trainquery, values)

    conn.commit()

