import uuid
from typing import Any, Dict, List

import chromadb
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Initializations
# ---------------------------------------------------------------------------
embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")

client = chromadb.PersistentClient(path="./vectordb")
collection = client.get_or_create_collection(name="enterprise_ai_os")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
)


# ---------------------------------------------------------------------------
# Helper: Build Google Services with OAuth Token
# ---------------------------------------------------------------------------
def get_google_service(service_name: str, version: str, access_token: str):
    """Builds a Google API service client using an OAuth access token."""
    creds = Credentials(token=access_token)
    return build(service_name, version, credentials=creds)


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

    # Initialize Services using valid OAuth credentials
    gmail = get_google_service("gmail", "v1", token)
    calendar = get_google_service("calendar", "v3", token)
    drive = get_google_service("drive", "v3", token)

    # 1. Fetch Gmail Messages
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
            # Extract snippet / subject for structured text representation
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

    # 2. Fetch Calendar Events
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

    # 3. Fetch Drive Files
    try:
        files_response = (
            drive.files()
            .list(pageSize=100, fields="files(id, name, mimeType, description)")
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

    # 4. Chunk Documents
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

    # 5. Embed & Vector Store (Only proceed if chunks exist)
    if chunks:
        texts_to_embed = [c["text"] for c in chunks]
        embeddings = embedding_model.encode(texts_to_embed).tolist()

        # Generate unique IDs to prevent indexing collisions
        unique_ids = [f"{c['source']}_{c['id']}_{uuid.uuid4().hex[:8]}" for c in chunks]

        collection.add(
            ids=unique_ids,
            documents=texts_to_embed,
            embeddings=embeddings,
            metadatas=[
                {
                    "source": c["source"],
                    "doc_id": c["id"],
                    "user": user_email,
                }
                for c in chunks
            ],
        )

    # Extract Latest Previews Safely
    latest_email = next((d["text"][:500] for d in docs if d["source"] == "gmail"), None)
    latest_calendar = next((d["text"][:500] for d in docs if d["source"] == "calendar"), None)
    latest_drive = next((d["text"][:500] for d in docs if d["source"] == "drive"), None)

    return {
        "response": "Knowledge base synchronized successfully.",
        "latest_email": latest_email,
        "latest_calendar": latest_calendar,
        "latest_drive": latest_drive,
        "documents_synced": len(docs),
        "chunks_created": len(chunks),
    }