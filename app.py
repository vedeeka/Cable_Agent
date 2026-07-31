import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from pydantic import BaseModel

from graph import graph

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

FRONTEND_URL = "http://localhost:3000"
BACKEND_URL = "http://localhost:8000"

app = FastAPI(
    title="Enterprise AI OS API",
    description="REST API for Enterprise AI OS supporting external dashboard integrations.",
    version="1.0.0"
)

# ---------------------------------------------------------------------------
# 1. CORS Configuration (Must allow credentials and match FRONTEND_URL exactly)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 2. Session Middleware Configuration
# ---------------------------------------------------------------------------
# Fallback to a stable local key if SECRET_KEY environment variable is missing.
# If SECRET_KEY is None, SessionMiddleware raises an AssertionError.
SECRET_KEY = os.getenv("SECRET_KEY")

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="session",
    same_site="lax",  
    https_only=False, 
    max_age=60 * 60 * 24,
)

oauth = OAuth()

google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": (
            "openid "
            "email "
            "profile "
            "https://www.googleapis.com/auth/gmail.readonly "
            "https://www.googleapis.com/auth/calendar.readonly "
            "https://www.googleapis.com/auth/drive.readonly "
            "https://www.googleapis.com/auth/documents.readonly "
            "https://www.googleapis.com/auth/spreadsheets.readonly"
        )
    },
)

# ---------------------------------------------------------------------------
# Models & Routes
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str

class ManualSyncRequest(BaseModel):
    name: Optional[str] = "User"
    email: str
    access_token: str
    refresh_token: Optional[str] = None


@app.get("/")
async def root(request: Request):
    user = request.session.get("user")
    return {
        "status": "online",
        "authenticated": user is not None,
        "user": user
    }


@app.get("/login")
async def login(request: Request):
    redirect_uri = f"{BACKEND_URL}/authorize"
    return await oauth.google.authorize_redirect(
        request,
        redirect_uri,
        access_type="offline",
        prompt="consent",
    )


@app.get("/authorize")
async def authorize(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        userinfo = token.get("userinfo")

        if not userinfo:
            userinfo = await oauth.google.parse_id_token(request, token)

        if not userinfo:
            resp = await oauth.google.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                token=token,
            )
            userinfo = resp.json()

        request.session["user"] = {
            "sub": userinfo.get("sub"),
            "name": userinfo.get("name"),
            "email": userinfo.get("email"),
            "picture": userinfo.get("picture"),
            "access_token": token.get("access_token"),
            "refresh_token": token.get("refresh_token"),
        }
        
        return RedirectResponse(f"{FRONTEND_URL}/dashboard")
    except Exception as e:
        print("Authorization Error:", e)
        return RedirectResponse(f"{FRONTEND_URL}/?error=auth_failed")


@app.get("/api/me")
async def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Not authenticated"
        )
    return {"user": user}


@app.get("/api/dashboard")
async def dashboard_api(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Please log in first."
        )

    initial_state = {
        "messages": [],
        "user_id": user.get("sub", user.get("email")),
        "name": user.get("name", "User"),
        "email": user.get("email", ""),
        "access_token": user.get("access_token", ""),
        "refresh_token": user.get("refresh_token"),
        "integrations": {
            "gmail": True,
            "calendar": True,
            "drive": True,
            "docs": True,
            "sheets": True,
        },
        "query": "Initialize user workspace",
        "intent": "startup",
        "plan": [],
        "next_step": 0,
        "context": "",
        "tool_results": {},
        "response": "",
    }

    try:
        raw_result = graph.invoke(initial_state)
        result = raw_result if isinstance(raw_result, dict) else {}
    except Exception as e:
        print("Graph invocation failed:", e)
        result = {}
    
    tool_results = result.get("tool_results", {})
    if not isinstance(tool_results, dict):
        tool_results = {}

    return {
        "status": "success",
        "user": user,
        "latest_email": result.get("latest_email") or tool_results.get("latest_email") or "No recent email found",
        "latest_calendar": result.get("latest_calendar") or tool_results.get("latest_calendar") or "No recent event found",
        "latest_drive": result.get("latest_drive") or tool_results.get("latest_drive") or "No recent drive file found",
        "latest_sheets": result.get("latest_sheets") or tool_results.get("latest_sheets") or "No sheets data found",
        "documents_synced": result.get("documents_synced") or tool_results.get("documents_synced") or 0,
        "chunks_created": result.get("chunks_created") or tool_results.get("chunks_created") or 0,
        "response_msg": result.get("response") or "Workspace loaded.",
    }


@app.post("/api/sync")
async def manual_sync_api(payload: ManualSyncRequest):
    initial_state = {
        "messages": [],
        "user_id": payload.email,
        "name": payload.name,
        "email": payload.email,
        "access_token": payload.access_token,
        "refresh_token": payload.refresh_token,
        "integrations": {
            "gmail": True,
            "calendar": True,
            "drive": True,
            "docs": True,
            "sheets": True,
        },
        "query": "Initialize user workspace",
        "intent": "startup",
        "plan": [],
        "next_step": 0,
        "context": "",
        "tool_results": {},
        "response": "",
    }

    try:
        raw_result = graph.invoke(initial_state)
        result = raw_result if isinstance(raw_result, dict) else {}
    except Exception as e:
        print("Sync error:", e)
        result = {}

    return {
        "status": "success",
        "latest_email": result.get("latest_email", "No recent email found"),
        "latest_calendar": result.get("latest_calendar", "No recent event found"),
        "latest_drive": result.get("latest_drive", "No recent drive file found"),
        "documents_synced": result.get("documents_synced", 0),
        "chunks_created": result.get("chunks_created", 0),
        "response_msg": result.get("response", "Workspace loaded."),
    }


@app.post("/api/chat")
async def chat_api(payload: ChatRequest, request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Please log in first."
        )

    state = {
        "messages": [],
        "user_id": user.get("email"),
        "name": user.get("name"),
        "email": user.get("email"),
        "access_token": user.get("access_token"),
        "refresh_token": user.get("refresh_token"),
        "integrations": {
            "gmail": True,
            "calendar": True,
            "drive": True,
            "docs": True,
            "sheets": True,
        },
        "query": payload.message,
        "intent": "",
        "plan": [],
        "next_step": 0,
        "context": "",
        "tool_results": {},
        "response": "",
    }

    try:
        result = graph.invoke(state)
        return result if isinstance(result, dict) else {"response": "Error processing query."}
    except Exception as e:
        print("Chat processing error:", e)
        raise HTTPException(status_code=500, detail="Internal processing error.")


@app.get("/logout")
@app.post("/api/logout")
async def logout(request: Request):
    request.session.clear()
    return {"status": "success", "message": "Successfully logged out."}


if __name__ == "__main__":
    import uvicorn
    # Keep host aligned strictly to "localhost" to match FRONTEND_URL same-site context
    uvicorn.run("app:app", host="localhost", port=8000, reload=True)