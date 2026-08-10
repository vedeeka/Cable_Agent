from langchain.tools import tool
import requests

@tool
def get_google_sheet(access_token: str, spreadsheet_id: str, sheet_range: str):
    """
    Get values from a Google Sheet.

    Args:
        access_token: Google OAuth access token.
        spreadsheet_id: Google Spreadsheet ID.
        sheet_range: Range to read (e.g. 'Sheet1!A1:D10').
    """

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/"
        f"{spreadsheet_id}/values/{sheet_range}"
    )

    r = requests.get(url, headers=headers)

    return r.json()