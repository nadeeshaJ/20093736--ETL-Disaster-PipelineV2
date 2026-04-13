from datetime import datetime
import os
import pandas as pd
import requests
import logging

def gdcs_extraction():
    logging.info("Downloading advanced GDACS alerts...")
    api_url = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH" 
    params = {
        "fromdate": "2025-01-01",
        "todate": datetime.now().strftime("%Y-%m-%d"), 
        "alertlevel": "Green,Orange,Red",
          "format": "json"
    }
    
    response = requests.get(api_url, params=params, timeout=60)
    response.raise_for_status()
    data = response.json()
    events = data.get("features", [])
    rows = []
# select event, name, type, country, severity, alert, magnitude, from_date columns only
    for event in events: 
        props = event.get("properties", {})
        geom = event.get("geometry", {})
        coords = geom.get("coordinates", [None, None])
        severity_data = props.get("severitydata", {})
        
        rows.append({
            "event_id": str(props.get("eventid")),
            "glide_no": props.get("glideno"), 
            "country": props.get("country"),
            "iso3": props.get("iso3"),
            "disaster_type": props.get("eventtype"),
            "alert_level": props.get("alertlevel"),
            "severity": props.get("severity"),
            "magnitude": severity_data.get("severity", 0), # magnitude
            "magnitude_unit": severity_data.get("severityunit"), # units : Mw or km/h
            "population": props.get("population"),
            "start_date": props.get("fromdate"),
            "end_date": props.get("todate"),
            "latitude": coords[1] if len(coords) > 1 else None,
            "longitude": coords[0] if len(coords) > 0 else None
        })

# shape into pandas dataframe
    df = pd.DataFrame(rows)
    # create folder if does not exist
    os.makedirs("data/raw/gdacs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")# save files names with time
    output_path = f"data/raw/gdacs/gdacs_{timestamp}.csv"
    df.to_csv(output_path, index=False)# csv file
    
    logging.info(f"GDACS Data Saved: {output_path}")
    return df, output_path

# default function
# if __name__ == "__main__":
#     gdcs_extraction()