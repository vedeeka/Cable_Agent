import time
import uuid
from typing import Any, Dict, List

import chromadb
import google_auth_httplib2
import httplib2
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from Tools.summarization.summarizer import summarizer





embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")

client = chromadb.PersistentClient(path="./vectordb")
collection = client.get_or_create_collection(name="enterprise_ai_os")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
)


# ---------------------------------------------------------------------------
# Helper: Build Google Services with Authorized Transport and Timeout
# ---------------------------------------------------------------------------
def get_google_service(service_name: str, version: str, access_token: str, timeout: int = 90):
    """Builds a Google API service client using an authorized transport layer to avoid parameter conflict."""
    creds = Credentials(token=access_token)
    http_transport = httplib2.Http(timeout=timeout)
    authorized_http = google_auth_httplib2.AuthorizedHttp(creds, http=http_transport)
    return build(service_name, version, http=authorized_http)


def get_google_sheets_service(access_token: str, timeout: int = 90):
    creds = Credentials(token=access_token)
    http_transport = httplib2.Http(timeout=timeout)
    authorized_http = google_auth_httplib2.AuthorizedHttp(creds, http=http_transport)
    return build("sheets", "v4", http=authorized_http)


# ---------------------------------------------------------------------------
# Helper: Fetch Sheet Values with Retry Logic
# ---------------------------------------------------------------------------
def fetch_sheet_values_with_retry(sheets_service, spreadsheet_id: str, sheet_range: str, max_retries: int = 3):
    """Fetches cell values with retry logic in case of transient network or timeout issues."""
    for attempt in range(max_retries):
        try:
            result = (
                sheets_service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=sheet_range)
                .execute()
            )
            return result.get("values", [])
        except Exception as e:
            if attempt < max_retries - 1:
                sleep_time = 2 ** attempt
                print(f"Read attempt {attempt + 1} failed for {spreadsheet_id} (Range: {sheet_range}): {e}. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
                continue
            raise e
    return []


# ---------------------------------------------------------------------------
# State Nodes
# ---------------------------------------------------------------------------
def startup_node(state: Dict[str, Any]) -> Dict[str, Any]:
    print("Logged in:", state["email"])
    return {"context": f"User {state['name']} has connected Google."}


def welcome_node(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "response": f"Welcome {state['name']}! Google account connected successfully."
    }


def sync_everything_node(state: Dict[str, Any]) -> Dict[str, Any]:
    
    token = state["access_token"]
    user_email = state["email"]
    docs: List[Dict[str, Any]] = []

    # Initialize Services using valid OAuth credentials and safe timeouts
    gmail = get_google_service("gmail", "v1", token, timeout=60)
    calendar = get_google_service("calendar", "v3", token, timeout=60)
    drive = get_google_service("drive", "v3", token, timeout=90)
    sheets = get_google_service("sheets", "v4", token, timeout=120)  # Safe timeout for large sheets

    # ---------------------------------------------------------------------------
    # 0. Fetch Google Sheets
    # ---------------------------------------------------------------------------
    try:
        sheet_files = (
            drive.files()
            .list(
                q="mimeType='application/vnd.google-apps.spreadsheet'",
                pageSize=100,
                fields="files(id, name)"
            )
            .execute()
            .get("files", [])
        )

        print(f"Found {len(sheet_files)} spreadsheet files in Google Drive.")

        for sheet in sheet_files:
            spreadsheet_id = sheet["id"]
            spreadsheet_name = sheet["name"]

            try:
                # Get spreadsheet metadata to list tabs
                metadata = (
                    sheets.spreadsheets()
                    .get(spreadsheetId=spreadsheet_id)
                    .execute()
                )

                worksheets = metadata.get("sheets", [])
                MAX_TABS = 10

                for worksheet in worksheets[:MAX_TABS]:
                    sheet_title = worksheet["properties"]["title"]

                    # Escape single quotes in tab titles and request columns A through Z.
                    # This prompts Google Sheets to return only rows containing active data.
                    escaped_title = sheet_title.replace("'", "''")
                    safe_range = f"'{escaped_title}'!A:Z"

                    rows = fetch_sheet_values_with_retry(
                        sheets_service=sheets,
                        spreadsheet_id=spreadsheet_id,
                        sheet_range=safe_range,
                        max_retries=3
                    )

                    if not rows:
                        print(f"No data returned for sheet '{spreadsheet_name}' -> tab '{sheet_title}'")
                        continue

                    sheet_text = "\n".join(
                        ", ".join(map(str, row)) for row in rows
                    )

                    docs.append(
                        {
                            "text": (
                                f"Spreadsheet: {spreadsheet_name}\n"
                                f"Sheet: {sheet_title}\n\n"
                                f"{sheet_text}"
                            ),
                            "source": "sheets",
                            "id": spreadsheet_id,
                        }
                    )
                    print(f"Successfully processed {len(rows)} rows from sheet '{spreadsheet_name}' -> tab '{sheet_title}'")

            except Exception as e:
                print(f"Error reading sheet '{spreadsheet_name}' tab '{sheet_title}': {e}")

    except Exception as e:
        print(f"Error listing spreadsheets: {e}")

    # ---------------------------------------------------------------------------
    # 1. Fetch Gmail Messages
    # ---------------------------------------------------------------------------
    try:
        messages_response = (
            gmail.users()
            .messages()
            .list(userId="me", maxResults=20)
            .execute()
        )
        messages = messages_response.get("messages", [])

        for m in messages:
            msg = (
                gmail.users()
                .messages()
                .get(userId="me", id=m["id"], format="full")
                .execute()
            )
            snippet = msg.get("snippet", "")
            docs.append(
                {
                    "text": f"Gmail Message ID: {m['id']}\nSnippet: {snippet}",
                    "source": "gmail",
                    "id": m["id"],
                }
            )
    except Exception as e:
        print(f"Error fetching Gmail: {e}")

    # ---------------------------------------------------------------------------
    # 2. Fetch Calendar Events
    # ---------------------------------------------------------------------------
    try:
        events_response = (
            calendar.events()
            .list(calendarId="primary", maxResults=20)
            .execute()
        )
        events = events_response.get("items", [])

        for e in events:
            summary = e.get("summary", "No Title")
            description = e.get("description", "")
            start = e.get("start", {}).get("dateTime", e.get("start", {}).get("date", ""))
            
            content = f"Event: {summary}\nStart Time: {start}\nDescription: {description}"
            docs.append(
                {
                    "text": content,
                    "source": "calendar",
                    "id": e["id"],
                }
            )
    except Exception as e:
        print(f"Error fetching Calendar: {e}")

    # ---------------------------------------------------------------------------
    # 3. Fetch Drive Files
    # ---------------------------------------------------------------------------
    try:
        files_response = (
            drive.files()
            .list(pageSize=100, fields="files(id, name, mimeType)")
            .execute()
        )
        files = files_response.get("files", [])

        for f in files:
            name = f.get("name", "Untitled")
            mime_type = f.get("mimeType", "")
            content = f"File Name: {name}\nType: {mime_type}"
            
            docs.append(
                {
                    "text": content,
                    "source": "drive",
                    "id": f["id"],
                }
            )
    except Exception as e:
        print(f"Error fetching Drive: {e}")

    # ---------------------------------------------------------------------------
    # 4. Chunk Documents
    # ---------------------------------------------------------------------------
    chunks = []
    for d in docs:
        for chunk_text in splitter.split_text(d["text"]):
            chunks.append(
                {
                    "text": chunk_text,
                    "source": d["source"],
                    "id": d["id"],
                }
            )

    latest_email = next((d["text"][:500] for d in docs if d["source"] == "gmail"), None)
    latest_calendar = next((d["text"][:500] for d in docs if d["source"] == "calendar"), None)
    latest_drive = next((d["text"][:500] for d in docs if d["source"] == "drive"), None)
    latest_sheets = next((d["text"][:500] for d in docs if d["source"] == "sheets"), None)

    if chunks:
        texts_to_embed = [c["text"] for c in chunks]
        embeddings = embedding_model.encode(texts_to_embed).tolist()
        unique_ids = [
            f"{c['source']}_{c['id']}_{uuid.uuid4().hex[:8]}"
            for c in chunks
        ]
        collection.add(
            ids=unique_ids,
            documents=texts_to_embed,
            embeddings=embeddings,
            metadatas=[
                {
                    "user_id": user_email,
                    "source": c["source"],
                    "doc_id": c["id"],
                    "chunk_id": i,
                    "timestamp": int(time.time())
                }
                for i, c in enumerate(chunks)
            ]
        )
        collection.add(
            ids=unique_ids,
            documents=texts_to_embed,
            embeddings=embeddings,
            metadatas=[
                {
                    "email": user_email,
                    "source": c["source"],
                    "doc_id": c["id"],
                    "latest_email": latest_email or "",
                    "latest_calendar": latest_calendar or "",
                    "latest_drive": latest_drive or "",
                    "latest_sheets": latest_sheets or "",
                    "documents_synced": len(docs),
                    "chunks_created": len(chunks),
                    "timestamp": int(time.time()),
                }
                for c in chunks
            ],
        )

    return {
        "response": "Knowledge base synchronized successfully.",
        "latest_email": latest_email,
        "latest_calendar": latest_calendar,
        "latest_drive": latest_drive,
        "latest_sheets": latest_sheets,
        "documents_synced": len(docs),
        "chunks_created": len(chunks),
    }


