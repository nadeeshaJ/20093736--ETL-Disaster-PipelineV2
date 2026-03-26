import os

import pandas as pd
import requests

# extract world bank data with indicators Net ODA recived and Net ODA recived as % of GNI
def get_worldbank(indicator):
     
    print("Downloading World Bank dataset:" , indicator)

    api_url = f"https://api.worldbank.org/v2/country/all/indicator/{indicator}?format=json&per_page=20000"
    response = requests.get(api_url)

    data = response.json()

    #print(data[0])
    #print(data[1])

    records = data[1]
    rows = []

    # select country, value, isoo3, year columns only
    for item in records: 
        rows.append(
            {
                "country" : item["country"]["value"],
                "iso3" : item["countryiso3code"],
                "year" : item["date"],
                "value" : item["value"]
            }
        )

    # shape into pandas dataframe
    df = pd.DataFrame(rows)

    # create folder if does not exist
    os.makedirs("data/raw/worldbank", exist_ok=True)


# indicators
def worldbank_indicators():

    # Net ODA recived 
    get_worldbank("DT.ODA.ALLD.CD")

    # Net ODA recived as % of GNI
    get_worldbank("DT.ODA.ODAT.GN.ZS")

# default function
if __name__ == "__main__":
    worldbank_indicators()