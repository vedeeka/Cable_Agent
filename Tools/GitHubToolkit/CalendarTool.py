from langchain.tools import tool
import requests


@tool
def get_calendar(access_token: str):

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    r = requests.get(
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        headers=headers,
    )

    return r.json()