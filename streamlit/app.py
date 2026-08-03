import streamlit as st
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

# get API key if needed
load_dotenv()
API_KEY = os.getenv("API_KEY")
if API_KEY is None:
    API_KEY = st.secrets["API_KEY"]

# get database location
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# check if weekday morning
now = datetime.now(timezone.utc)
is_weekday_morning = True if (now.day <= 4 and 6 <= now.hour < 10) else False

@st.cache_data(ttl=60)
def get_line_status(line_id):
    url = f"https://api.tfl.gov.uk/Line/{line_id}/Status"
    params = {"app_key": API_KEY}
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=20)
def find_arrivals(ids, stopPointId, direction=""):
    url=f"https://api.tfl.gov.uk/Line/{ids}/Arrivals/{stopPointId}?direction={direction}"
    params = {"app_key": API_KEY}
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.json()

status = get_line_status("district")[0]["lineStatuses"][0]["statusSeverityDescription"]

# if no trains exist
next_train = "No Train Showing"
destination = "District Line"

for train in find_arrivals("district", "940GZZLUSFS", direction="outbound"):
    dt = datetime.strptime(train["expectedArrival"], r"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    difference_seconds = int((dt-now).total_seconds())
    if difference_seconds < 60:
        continue
    else:
        next_train = difference_seconds//60
        destination = train["towards"]
        break

direct = False
if destination not in ["Out of Service", "District Line", "East Putney", "Putney Bridge", "Parsons Green", "Fulham Broadway", "West Brompton", "Earls Court", "High Street Kensington", "Edgware Road"]:
    direct = True

# for average headway and waiting time estimates
now_query = """
WITH fby AS (
    SELECT 
        device_query_time,
        time_to_station,
        LAG(time_to_station) OVER (PARTITION BY device_query_time ORDER BY time_to_station) AS prev_tts
    FROM arrivals
    WHERE station = "FBY"
    AND NOT COALESCE(direction, "N/A") = "inbound"
)
SELECT
    CASE 
        WHEN COUNT(*) = 1 THEN NULL 
        ELSE ROUND(SUM(COALESCE(time_to_station-prev_tts, 0)) / (COUNT(*)-1), 1) 
    END AS avg_headway,
    CASE 
        WHEN COUNT(*) = 1 THEN "N/A" 
        ELSE ROUND(SUM(COALESCE((time_to_station-prev_tts) * (time_to_station-prev_tts), 0)) / (2*(SUM(COALESCE(time_to_station-prev_tts, 0)))), 1)
    END AS avg_wait_time
FROM fby
GROUP BY device_query_time
ORDER BY device_query_time DESC
LIMIT 5
;
"""

day_query = """
WITH fby AS (
    SELECT 
        device_query_time,
        time_to_station,
        LAG(time_to_station) OVER (PARTITION BY device_query_time ORDER BY time_to_station) AS prev_tts
    FROM arrivals
    WHERE station = "FBY"
    AND NOT COALESCE(direction, "N/A") = "inbound"
),
kpis AS (
    SELECT
        CASE 
            WHEN COUNT(*) = 1 THEN NULL 
            ELSE ROUND(SUM(COALESCE(time_to_station-prev_tts, 0)) / (COUNT(*)-1), 1) 
        END AS avg_headway,
        CASE 
            WHEN COUNT(*) = 1 THEN "N/A" 
            ELSE ROUND(SUM(COALESCE((time_to_station-prev_tts) * (time_to_station-prev_tts), 0)) / (2*(SUM(COALESCE(time_to_station-prev_tts, 0)))), 1)
        END AS avg_wait_time,
        device_query_time
    FROM fby
    GROUP BY device_query_time
    ORDER BY device_query_time
)
SELECT 
    AVG(avg_headway),
    AVG(avg_wait_time)
FROM kpis
GROUP BY DATE(device_query_time)
ORDER BY DATE(device_query_time) DESC
LIMIT 5
;
"""
query_map = {
    "Now": now_query,
    "Day": day_query
}

slider = st.selectbox("KPI period", ["Now", "Day"])
query = query_map[slider]

if is_weekday_morning:
    # wrap inside a function to cache result
    @st.cache_data(ttl=120)
    def find_kpis(query):
        with sqlite3.connect(DATA / "tfl_train_data.db") as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            kpis=cursor.fetchall()
            headways, waits = map(list, zip(*kpis))
        return headways, waits

    headways, waits = find_kpis(query)

    avg_wait = round(waits[0]/60, 1) if type(waits[0])!=str else "N/A"

    if "N/A" in waits:
        wait_delta_mins = "N/A"
    else:
        wait_delta_mins = str(round(waits[0]/60 - (sum(waits[1:])/240), 1)) + " mins" # takes the last wait times from database, potentially Friday for Monday 7am queries

    # make this a delta for positive time
    if wait_delta_mins[0].isnumeric():
        wait_delta_mins = "+" + wait_delta_mins

    avg_headway = round(headways[0]/60, 1) if type(headways[0])!=str else "N/A"

    if "N/A" in headways:
        headway_delta_mins = "N/A"
    else:
        headway_delta_mins = str(round(headways[0]/60 - (sum(headways[1:])/(240)), 1)) + " mins"

    # make this a delta for positive time
    if headway_delta_mins[0].isnumeric():
        headway_delta_mins = "+" + headway_delta_mins
        
else:
    avg_wait = "N/A"
    avg_headway = "N/A"
    wait_delta_mins = None
    headway_delta_mins = None

# streamlit app
st.title("Southfields Underground Station")

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.metric(
            "🚆 Next Eastbound Train",
            f"{next_train} min{'' if next_train == 1 else 's'}",
        )

    with st.container(border=True):
        st.metric(
            "📍 Destination",
            destination,
            delta="Direct" if direct else None,
            delta_color="normal",
        )

with col2:
    with st.container(border=True):
        st.metric(
            "📊 Avg. Headway",
            f"Est. {avg_headway} mins",
            delta=headway_delta_mins,
            delta_color="inverse",
        )

    with st.container(border=True):
        st.metric(
            "⏱️ Avg. Wait Time",
            f"Est. {avg_wait} mins",
            delta=wait_delta_mins,
            delta_color="inverse",
        )

st.markdown(f"TFL status: District Line - {status}")
st.markdown("Headway and Wait Time estimates available 7am-11am on weekdays")

with st.sidebar:
    st.text("Powered by TfL Open Data")
    st.text("Contains OS data © Crown copyright and database rights 2016 and Geomni UK Map data © and database rights [2019]")