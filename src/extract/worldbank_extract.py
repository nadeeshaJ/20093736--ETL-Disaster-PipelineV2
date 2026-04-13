from datetime import datetime
from pathlib import Path
import pandas as pd
import requests

# extract world bank data with indicators Net ODA recived and Net ODA recived as % of GNI

def get_timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def get_worldbank_data(indicator_code):
     
    print("Downloading World Bank dataset:" , indicator_code)

    api_url = f"https://api.worldbank.org/v2/country/all/indicator/{indicator_code}?format=json&per_page=20000"
    response = requests.get(api_url, timeout= 60)
    response.raise_for_status()
    data = response.json()

    #print(data[0])
    #print(data[1])

    records = data[1]
    rows = []

    # select country, value, isoo3, year columns only
    if len(records) > 1:
        for item in records: 
            rows.append(
                {
                    "country" : item["country"]["value"] if item.get("country") else None,
                    "iso3" : item["countryiso3code"],
                    "year" : item["date"],
                    "value" : item["value"],
                    "indicator" : indicator_code
                }
            )

    # shape into pandas dataframe
    df = pd.DataFrame(rows)
    return df

# data extraction
def worldbank_extraction():
    save_folder = Path("data/raw/worldbank")
    # create folder if does not exist
    save_folder.mkdir(parents=True, exist_ok=True)

    indicators = {
        "DT.ODA.ALLD.CD": "oda_received_usd",
        "DT.ODA.ODAT.MP.ZS": "aid_dependency_percent_gni",
        "EG.ELC.ACCS.ZS": "electricity_access_pct" # reslicance proxy
    }
    
    for code, name in indicators.items():
        df = get_worldbank_data(code)
        file_path = save_folder / f"{name}_{get_timestamp()}.csv" # csv file
        df.to_csv(file_path, index=False)
        print("Saved:", file_path)

# default function
# if __name__ == "__main__":
#     worldbank_extraction()