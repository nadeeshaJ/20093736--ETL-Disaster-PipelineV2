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

    print(data)
   



# default function
if __name__ == "__main__":
    get_gdcs()