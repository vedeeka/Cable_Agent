from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import httpx
from email.message import EmailMessage
import base64

router = APIRouter(prefix="/execute", tags=["Execute"])

class ExecuteRequest(BaseModel):
    action: str
    payload: dict

@router.post("/action")
async def execute_action(request: Request, body: ExecuteRequest):
    access_token = request.session.get('access_token')
    
    if not access_token:
        raise HTTPException(status_code=401, detail="Authentication token missing. Please log in again.")
        
    if body.action == "send_email":
        to_email = body.payload.get("to")
        body_text = body.payload.get("body", "Hi,\n\nI am reaching out to follow up on our recent discussion.\n\nBest regards,")
        
        if not to_email:
            raise HTTPException(status_code=400, detail="Missing 'to' email address.")
            
        # Create MIME message
        message = EmailMessage()
        message.set_content(body_text)
        message['To'] = to_email
        message['Subject'] = 'Follow up from Enterprise OS'
        
        # Base64 encode it for Gmail API
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"raw": encoded_message}
            )
            
            if response.status_code == 200:
                return {"status": "success", "detail": f"Email sent to {to_email}"}
            else:
                print(f"Gmail API error: {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Failed to send email via Gmail API")
                
    else:
        raise HTTPException(status_code=400, detail="Unsupported action")
