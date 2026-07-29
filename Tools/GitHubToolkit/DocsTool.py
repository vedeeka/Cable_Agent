from langchain.tools import tool
import requests


@tool
def get_document(doc_id: str, access_token: str):

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    r = requests.get(
        f"https://docs.googleapis.com/v1/documents/{doc_id}",
        headers=headers,
    )

    return r.json()