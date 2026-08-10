from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.api import organizations, users
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

from fastapi import Request
from fastapi.responses import JSONResponse

@app.get("/api/dashboard")
def get_dashboard(request: Request):
    user = request.session.get('user')
    if not user:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    
    return {
        "status": "Healthy",
        "user": {
            "sub": user.get("sub", "unknown"),
            "name": user.get("name", "Jane Doe"),
            "email": user.get("email", "jane@example.com"),
            "picture": user.get("picture", "")
        },
        "latest_email": "Project Athena kickoff notes (3 hrs ago)",
        "latest_calendar": "Q3 Planning with Execs (Tomorrow, 10 AM)",
        "latest_drive": "Enterprise_AI_OS_Architecture.pdf",
        "latest_sheets": "Q2_Financials_v3 (Updated by Alice)",
        "documents_synced": 4280,
        "chunks_created": 148500,
        "response_msg": "All cognitive nodes are running optimally."
    }

@app.get("/")
def root():
    return {"message": "Welcome to Enterprise AI OS"}

