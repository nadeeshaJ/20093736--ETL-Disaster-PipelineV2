from datetime import datetime
import os
import pandas as pd
import requests

# extract current disaster alerts from GDACS
def get_gdcs():
     
    print("Downloading GDACS alerts")

    api_url = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
    response = requests.get(api_url)

    data = response.json()

    #print(data)

    features = data["features"]
    rows = []

    # select event, name, type, country, severity, alert, from_date columns only
    for feature in features: 
        properties = feature["properties"]

        rows.append(
            {
                "event_id" : properties.get("eventid"),
                "name" : properties.get("name"),
                "type" : properties.get("eventtype"),
                "country" : properties.get("country"),
                "alert" : properties.get("alertlevel"),
                "from_date" : properties.get("fromdate")
            }
        )

    # shape into pandas dataframe
    df = pd.DataFrame(rows)

    # create folder if does not exist
    os.makedirs("data/raw/gdacs", exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") # save files names with time
    file_name = f"data/raw/gdacs/gdacs_{timestamp}.csv"
    
    
    df.to_csv(file_name, index=False) # csv file
    print("GDACS Data: ", file_name)
   



# default function
if __name__ == "__main__":
    get_gdcs()