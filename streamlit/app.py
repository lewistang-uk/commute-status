import streamlit as st
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()
API_KEY = os.getenv("API_KEY")

def get_line_status(line_id):
    url = f"https://api.tfl.gov.uk/Line/{line_id}/Status"
    params = {"app_key": API_KEY}
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.json()

def find_arrivals(ids, stopPointId, direction=""):
    url=f"https://api.tfl.gov.uk/Line/{ids}/Arrivals/{stopPointId}?direction={direction}"
    params = {"app_key": API_KEY}
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.json()

status = get_line_status("district")[0]["lineStatuses"][0]["statusSeverityDescription"]
next_train = "N/A"
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

cols = st.columns(3)

metrics = [
    ("Time until Next Train", str(next_train)+" minutes"),
    ("Destination", destination),
    ("Status", status),
]

for col, (label, value) in zip(cols, metrics):
    with col:
        with st.container(border=True):
            st.metric(label, value)