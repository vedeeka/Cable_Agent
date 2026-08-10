from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])

oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/spreadsheets'
    }
)

@router.get("/login")
async def login(request: Request):
    # Redirect to Google's consent screen
    redirect_uri = request.url_for('auth_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri, prompt="select_account")

@router.get("/callback", name="auth_callback")
async def auth_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        user = token.get('userinfo')
        if user:
            request.session['user'] = user
            request.session['access_token'] = token.get('access_token')
    except Exception as e:
        print(f"Auth error: {e}")
    # Redirect to frontend dashboard
    return RedirectResponse(url="http://localhost:3000/dashboard")

@router.get("/me")
async def get_current_user(request: Request):
    user = request.session.get('user')
    if user:
        return {
            "user": {
                "id": user.get("sub"),
                "name": user.get("name"),
                "email": user.get("email"),
                "role": "admin" # Default mock role
            },
            "permissions": ["doc_read"]
        }
    
    raise HTTPException(status_code=401, detail="Not authenticated")

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="http://localhost:3000/")
