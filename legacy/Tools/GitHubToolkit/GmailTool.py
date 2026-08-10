from langchain.tools import tool
import requests

@tool
def get_emails(access_token: str):
    """Get top latest recent full Gmail messages."""

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    r = requests.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        headers=headers,
    )

    return r.json()