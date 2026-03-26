from datetime import datetime
import os
import requests


# download EM-DAT data from https://public.emdat.be/data 

def downlod_emdat() :

    print("Downloading EM-DAT dataset")

    api_url = "https://data.humdata.org/api/3/action/package_show?id=emdat-country-profiles"
    response = requests.get(api_url)

    # print(response.status_code)

    data = response.json()

    #print(data.keys())

    resources = data["result"]["resources"]

    #print(resources)

    # find downloadable link with .xlsx format from resources
    file_url = None

    for res in resources :
        url = res.get("download_url")
        #print(f"Checking: {url}")
        if url and (url.endswith(".xlsx") or url.endswith(".csv")) :
            file_url = url
            break

    # file not found error validation
    if file_url is None :
        print("Em_DAT file not found")
        return
    
    file_data = requests.get(file_url).content

    # create folder if does not exist
    os.makedirs("data/raw/emdat", exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") # save files names with time
    file_name = f"data/raw/emdat/emdat_{timestamp}.xlsx"
    
    with open(file_name , "wb") as f:
        f.write(file_data)
    print("EM-DAT Data: ", file_name)

# default function
if __name__ == "__main__":
    downlod_emdat()

