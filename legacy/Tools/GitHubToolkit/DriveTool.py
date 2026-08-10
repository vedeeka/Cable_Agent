
from langchain.tools import tool
import requests
@tool
def get_drive_files(access_token: str):

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    r = requests.get(
        "https://www.googleapis.com/drive/v3/files",
        headers=headers,
    )

    return r.json()