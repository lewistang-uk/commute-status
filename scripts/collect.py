# What if historical data was collected and stored? This would give a better estimate of average wait time than any snapshot in time.
# Powered by Tfl Open Data

import sqlite3
import requests

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
        current_time TEXT,
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
        current_time, 
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
        for train in arrivals:
            values = (station, train["timestamp"], train["expectedArrival"], train["timeToStation"], train["direction"], train["towards"], train["currentLocation"])
            cursor.execute(trainquery, values)

    conn.commit()

