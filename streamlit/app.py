import streamlit as st
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()
API_KEY = os.getenv("API_KEY")

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

direct = False
if destination not in ["Edgware Road", "District Line", "Out of Service", "High Street Kensington"]:
    direct = True

# for upper bound on average waiting time - can be estimated by halving the train headway at Fulham Broadway (like past departures)
timetostation = []
avg_wait = "N/A"
for train in find_arrivals("district", "940GZZLUFBY", direction="outbound"):
    timetostation.append(train["timeToStation"])

timetostation = sorted(timetostation)
# if only one train on the departure board, this is the MLE of exp. waiting time
if len(timetostation)==1:
    avg_wait = timetostation[0]
    
    # otherwise find the average difference, assuming uniform distribution of passenger arrival to station
else:
    avg_wait = round(
        (timetostation[-1] - timetostation[0]) / (120*(len(timetostation)-1)),
        1
    ) # /60 for minutes, /2 for average wait time, total /120

# find any suspected delays at Southfields, using following stations as a predictor
waits = []
for stop in ["940GZZLUEPY", "940GZZLUPYB"]: # only two queries for better usability
    for train in find_arrivals("district", stop, direction="outbound"): 
        dt = datetime.strptime(train["expectedArrival"], r"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        difference_seconds = int((dt-now).total_seconds())
        waits.append(difference_seconds)

if waits:
    min_wait = min(waits)
    if min_wait < -60:
        predicted_status = "Delays - dwell time at stations"
    elif min_wait > 326:
        predicted_status = "Delays - train frequency"
    else:
        predicted_status = "Good Service"
else:
    predicted_status = "No Trains"

# streamlit app
st.markdown("""
<style>
.stApp {
    background-color: #d0f2d9;
}
</style>
""", unsafe_allow_html=True)

st.title("Southfields Underground Station")

with st.container(border=True):
    st.metric("Next Eastbound Train", str(next_train)+" minute" + ("" if next_train == 1 else "s"))

with st.container(border=True):
    st.metric("Destination", destination, delta="Direct" if direct else None, delta_color="normal")

with st.container(border=True):
    st.metric("Avg Wait Time", "<" + str(avg_wait) + " minutes")

st.markdown(f"TFL status: District Line - {status}")
st.markdown(f"Predicted status: District Line - {predicted_status}")

with st.sidebar:
    st.text("Powered by TfL Open Data")
    st.text("Contains OS data © Crown copyright and database rights 2016 and Geomni UK Map data © and database rights [2019]")