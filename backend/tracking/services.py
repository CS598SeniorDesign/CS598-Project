import requests
import xml.etree.ElementTree as ElementTree
from django.conf import settings

VALID_STATUS_CODE = 200


def fetch_bgg_plays(user: str, bgg_username: str):
    url: str = f"https://boardgamegeek.com/xmlapi2/plays?username={bgg_username}"
    bgg_api_token = settings.BGG_API_TOKEN

    request_headers = {
        "User-Agent": "QuestLog/0.1",
        "Authorization": f"Bearer {bgg_api_token}"
    }

    response: requests.Response = requests.get(url=url, headers=request_headers)

    if response.status_code not in [VALID_STATUS_CODE, 202]:
        print("Failed to reach BGG API.")
        print(response.status_code)
        print(response.text)
        return False

    root = ElementTree.fromstring(response.content)

    print(root.tag)
    return True


def main():
    fetch_bgg_plays("test", "ureia")


if __name__ == "__main__":
    main()
