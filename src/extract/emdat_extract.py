import request




# download EM-DAT data from https://public.emdat.be/data 

def downlod_emdat() :

    print("Downloading EM-DAT dataset")

    api_url = "https://data.humdata.org/api/3/action/package_show?id=emdat-country-profiles"
    response = request.get(api_url)

   # print(response.status_code)

    data = response.json()

    print(data)

if __name__ == "__main__":
    downlod_emdat()

