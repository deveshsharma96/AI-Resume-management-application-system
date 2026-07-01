import requests


def get_location_from_pincode(country, pincode):

    if country.lower() not in ["india", "in"]:
        return None

    url = f"https://api.postalpincode.in/pincode/{pincode}"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()

    except Exception:
        return None

    if not isinstance(data, list) or len(data) == 0:
        return None

    first = data[0]

    if first.get("Status") != "Success":
        return None

    post_offices = first.get("PostOffice")

    if not post_offices:
        return None

    po = post_offices[0]

    return {
        "city": po.get("Name"),
        "district": po.get("District"),
        "state": po.get("State"),
        "country": po.get("Country"),
        "pincode": po.get("Pincode")
    }