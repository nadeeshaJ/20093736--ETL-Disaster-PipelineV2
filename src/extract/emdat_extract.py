from datetime import datetime
import os
import requests


# extract EM-DAT data from https://public.emdat.be/data 

def downlod_emdat() :

    print("Downloading EM-DAT dataset")

    api_url = "https://data.humdata.org/api/3/action/package_show?id=emdat-country-profiles"
    response = requests.get(api_url, timeout= 60)
    response.raise_for_status()

    data = response.json()
    resources = data["result"]["resources"]

    # find downloadable link with .xlsx format from resources
    file_url = None
    version_label = None

    for res in resources :
        url = res.get("download_url")
        description = res.get("description", "")
        
        if url and (url.endswith(".xlsx") or url.endswith(".csv")) :
            file_url = url
            version_label = description
            break

    # file not found error validation
    if file_url is None :
        raise Exception("Em_DAT file not found.")

    # create folder if does not exist
    os.makedirs("data/raw/emdat", exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") # save files names with time
    output_path  = f"data/raw/emdat/emdat_{timestamp}.xlsx"

    file_data = requests.get(file_url, timeout=120)
    file_data.raise_for_status()
    
    with open(output_path  , "wb") as f:
        f.write(file_data.content)
    print("EM-DAT downloaded: ", output_path)
    print("Version:", version_label)
    return output_path

# default function
# if __name__ == "__main__":
#     downlod_emdat()

