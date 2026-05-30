import requests
import pandas as pd

PACKAGE_ID = "road-reconstruction-program"

def fetch_open_toronto_package():
    url = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show"
    params = {"id": PACKAGE_ID}

    response = requests.get(url, params=params)
    response.raise_for_status()

    return response.json()["result"]

def download_first_csv():
    package = fetch_open_toronto_package()

    resources = package["resources"]

    csv_resources = [
        r for r in resources
        if r.get("format", "").lower() in ["csv", "geojson", "json"]
    ]

    print("Available resources:")
    for r in csv_resources:
        print(r["name"], r.get("format"), r["url"])

    resource = csv_resources[0]
    data_url = resource["url"]

    df = pd.read_csv(data_url)
    df.to_csv("../data/open_toronto_permits.csv", index=False)

    print("Saved to ../data/open_toronto_permits.csv")
    print(df.head())

if __name__ == "__main__":
    download_first_csv()


