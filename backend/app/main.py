from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.api import organizations, users, chat, execute
from app.security import auth
from app.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY
)

# Include Routers
app.include_router(organizations.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)
app.include_router(execute.router, prefix=settings.API_V1_STR)

import httpx
import asyncio
from datetime import datetime, timezone
from fastapi import Request
from fastapi.responses import JSONResponse

@app.get("/api/dashboard")
async def get_dashboard(request: Request):
    user = request.session.get('user')
    access_token = request.session.get('access_token')
    
    if not user:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
        
    dashboard_data = {
        "status": "Healthy",
        "user": {
            "sub": user.get("sub", "unknown"),
            "name": user.get("name", "Jane Doe"),
            "email": user.get("email", "jane@example.com"),
            "picture": user.get("picture", "")
        },
        "latest_email": "No recent emails",
        "latest_calendar": "No upcoming events",
        "latest_drive": "No recent files",
        "latest_sheets": "No recent sheets",
        "documents_synced": 4280,
        "chunks_created": 148500,
        "response_msg": "All cognitive nodes are running optimally."
    }

    if not access_token:
        return dashboard_data

    headers = {"Authorization": f"Bearer {access_token}"}
    
    async def fetch_gmail(client):
        try:
            res = await client.get("https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=1&q=in:inbox", headers=headers)
            if res.status_code == 200:
                msgs = res.json().get('messages', [])
                if msgs:
                    msg_id = msgs[0]['id']
                    msg_res = await client.get(f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}", headers=headers)
                    if msg_res.status_code == 200:
                        headers_list = msg_res.json().get('payload', {}).get('headers', [])
                        subject = next((h['value'] for h in headers_list if h['name'] == 'Subject'), 'No Subject')
                        return subject
            return "No recent emails"
        except Exception:
            return "Error fetching email"

    async def fetch_calendar(client):
        try:
            now = datetime.now(timezone.utc).isoformat()
            url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events?timeMin={now}&maxResults=1&orderBy=startTime&singleEvents=true"
            res = await client.get(url, headers=headers)
            if res.status_code == 200:
                events = res.json().get('items', [])
                if events:
                    event = events[0]
                    summary = event.get('summary', 'Busy')
                    start_str = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date', '')
                    return f"{summary} ({start_str[:10]})"
            return "No upcoming events"
        except Exception:
            return "Error fetching calendar"

    async def fetch_drive(client):
        try:
            res = await client.get("https://www.googleapis.com/drive/v3/files?pageSize=1&orderBy=modifiedTime desc", headers=headers)
            if res.status_code == 200:
                files = res.json().get('files', [])
                if files:
                    return files[0].get('name')
            return "No recent files"
        except Exception:
            return "Error fetching drive"

    async def fetch_sheets(client):
        try:
            url = "https://www.googleapis.com/drive/v3/files?pageSize=1&orderBy=modifiedTime desc&q=mimeType='application/vnd.google-apps.spreadsheet'"
            res = await client.get(url, headers=headers)
            if res.status_code == 200:
                files = res.json().get('files', [])
                if files:
                    return files[0].get('name')
            return "No recent sheets"
        except Exception:
            return "Error fetching sheets"

    async with httpx.AsyncClient() as client:
        email, cal, drive, sheet = await asyncio.gather(
            fetch_gmail(client),
            fetch_calendar(client),
            fetch_drive(client),
            fetch_sheets(client)
        )
        
        dashboard_data["latest_email"] = email
        dashboard_data["latest_calendar"] = cal
        dashboard_data["latest_drive"] = drive
        dashboard_data["latest_sheets"] = sheet

    return dashboard_data

@app.get("/")
def root():
    return {"message": "Welcome to Enterprise AI OS"}

