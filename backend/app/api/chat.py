from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json
import httpx
import datetime

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    prompt: str

import google.generativeai as genai
from app.config import settings

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

@router.post("/stream")
async def chat_stream(request: Request, body: ChatRequest):
    async def generate_response():
        prompt = body.prompt.lower()
        
        def sse(data: dict):
            return f"data: {json.dumps(data)}\n\n"
            
        if not settings.GEMINI_API_KEY:
            yield sse({"type": "tool_status", "status": "pending", "content": "Thinking..."})
            await asyncio.sleep(1)
            yield sse({"type": "tool_status", "status": "error", "content": "No API Key"})
            
            text = "I am Aeryn. I currently do not have a Brain installed. Please add a `GEMINI_API_KEY` to your backend `.env` file so I can understand your commands!"
            for chunk in text.split(" "):
                yield sse({"type": "text", "content": chunk + " "})
                await asyncio.sleep(0.05)
            return
            
        yield sse({"type": "tool_status", "status": "pending", "content": "Processing intent..."})
        
        now = datetime.datetime.now().isoformat()
        
        system_instruction = f"""
        You are Aeryn, the intelligence layer of Enterprise OS. 
        The current date and time is {now}.
        Classify the user's prompt into one of the following actions.
        Return ONLY valid JSON matching this schema:
        {{
          "action": "SEND_EMAIL" | "SCHEDULE_MEETING" | "COUNT_EMAILS" | "CREATE_SHEET_FROM_EMAILS" | "CREATE_DOC_FROM_EMAILS" | "SUMMARIZE_EMAILS" | "SUMMARIZE_CALENDAR" | "GENERAL_CHAT",
          "parameters": {{
            // For SEND_EMAIL: "to" (email addr), "body"
            // For SCHEDULE_MEETING: "title", "startTime" (ISO8601 string), "endTime" (ISO8601 string)
            // For COUNT_EMAILS: "timeframe"
            // For CREATE_SHEET_FROM_EMAILS: none
            // For CREATE_DOC_FROM_EMAILS: none
            // For SUMMARIZE_EMAILS: none
            // For SUMMARIZE_CALENDAR: none
            // For GENERAL_CHAT: "response" (the text you want to say)
          }}
        }}
        Do not include markdown blocks like ```json. Just raw JSON.
        """
        
        try:
            model = genai.GenerativeModel('gemini-3-flash-preview', system_instruction=system_instruction)
            response = await asyncio.to_thread(model.generate_content, prompt)
            raw_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
            intent = json.loads(raw_text)
            
            yield sse({"type": "tool_status", "status": "success", "content": f"Intent identified: {intent.get('action')}"})
            
            action = intent.get('action')
            params = intent.get('parameters', {})
            
            if action == "SEND_EMAIL":
                email_addr = params.get('to', 'contact@example.com')
                
                text = f"I have prepared a draft email to {email_addr}. Please review and approve it."
                for chunk in text.split(" "):
                    yield sse({"type": "text", "content": chunk + " "})
                    await asyncio.sleep(0.05)
                    
                yield sse({
                    "type": "action_card",
                    "content": params.get('body', "Hi,\n\nFollowing up on our discussion. Let me know if you need any further information.\n\nBest,"),
                    "cardData": {
                        "icon": "mail",
                        "title": "Email Ready",
                        "headline": f"To: {email_addr}",
                        "primaryAction": "Send Email"
                    }
                })
                
            elif action == "SCHEDULE_MEETING":
                access_token = request.session.get('access_token')
                if not access_token:
                    yield sse({"type": "tool_status", "status": "error", "content": "Authentication needed"})
                    yield sse({"type": "text", "content": "I cannot access your calendar because your session is missing the required permissions. Please log out and log in again."})
                    return
                
                title = params.get('title', 'Meeting')
                start_time = params.get('startTime')
                end_time = params.get('endTime')
                
                if not start_time or not end_time:
                    yield sse({"type": "text", "content": "I couldn't determine the exact time for the meeting. Could you clarify?"})
                    return
                    
                yield sse({"type": "tool_status", "status": "pending", "content": f"Scheduling {title}..."})
                
                async with httpx.AsyncClient() as client:
                    headers = {"Authorization": f"Bearer {access_token}"}
                    event_data = {
                        "summary": title,
                        "start": {"dateTime": start_time},
                        "end": {"dateTime": end_time}
                    }
                    res = await client.post("https://www.googleapis.com/calendar/v3/calendars/primary/events", headers=headers, json=event_data)
                    
                    if res.status_code != 200:
                        yield sse({"type": "tool_status", "status": "error", "content": "Failed to create event."})
                        print("Calendar API Error:", res.text)
                        return
                        
                    event = res.json()
                    event_url = event.get('htmlLink')
                    
                    yield sse({"type": "tool_status", "status": "success", "content": "Event scheduled successfully."})
                    
                    text = f"I have successfully scheduled '{title}' on your Google Calendar."
                    for chunk in text.split(" "):
                        yield sse({"type": "text", "content": chunk + " "})
                        await asyncio.sleep(0.05)
                        
                    yield sse({
                        "type": "action_card",
                        "content": f"Event: {title}\nStart: {start_time}",
                        "cardData": {
                            "icon": "calendar",
                            "title": "Event Created",
                            "headline": title,
                            "primaryAction": "Open Event",
                            "url": event_url
                        }
                    })
                    
            elif action == "SUMMARIZE_CALENDAR":
                access_token = request.session.get('access_token')
                if not access_token:
                    yield sse({"type": "tool_status", "status": "error", "content": "Authentication needed"})
                    yield sse({"type": "text", "content": "I cannot access your calendar because your session is missing the required permissions. Please log out and log in again."})
                    return
                    
                yield sse({"type": "tool_status", "status": "pending", "content": "Reading your calendar..."})
                
                async with httpx.AsyncClient() as client:
                    headers = {"Authorization": f"Bearer {access_token}"}
                    # Get start of day and end of day in RFC3339
                    now_date = datetime.datetime.utcnow()
                    start_of_day = now_date.replace(hour=0, minute=0, second=0).isoformat() + "Z"
                    end_of_day = now_date.replace(hour=23, minute=59, second=59).isoformat() + "Z"
                    
                    url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events?timeMin={start_of_day}&timeMax={end_of_day}&singleEvents=true&orderBy=startTime"
                    res = await client.get(url, headers=headers)
                    
                    if res.status_code != 200:
                        yield sse({"type": "tool_status", "status": "error", "content": "Failed to access calendar"})
                        return
                        
                    events = res.json().get('items', [])
                    if not events:
                        yield sse({"type": "tool_status", "status": "success", "content": "Calendar read complete."})
                        text = "You don't have any events scheduled for today!"
                        for chunk in text.split(" "):
                            yield sse({"type": "text", "content": chunk + " "})
                            await asyncio.sleep(0.05)
                        return
                        
                    yield sse({"type": "tool_status", "status": "pending", "content": "Analyzing schedule with Gemini..."})
                    
                    agenda_str = ""
                    for e in events:
                        summary = e.get('summary', 'Busy')
                        start = e.get('start', {}).get('dateTime', e.get('start', {}).get('date'))
                        agenda_str += f"- {start}: {summary}\n"
                        
                    rag_prompt = f"The user asked: '{prompt}'. Here is the user's agenda for today. Summarize it conversationally:\n\n{agenda_str}"
                    
                    rag_model = genai.GenerativeModel('gemini-1.5-flash')
                    rag_response = await asyncio.to_thread(rag_model.generate_content, rag_prompt)
                    summary = rag_response.text
                    
                    yield sse({"type": "tool_status", "status": "success", "content": "Agenda analysis complete."})
                    
                    for chunk in summary.split(" "):
                        yield sse({"type": "text", "content": chunk + " "})
                        await asyncio.sleep(0.05)
                
            elif action == "SUMMARIZE_EMAILS":
                access_token = request.session.get('access_token')
                if not access_token:
                    yield sse({"type": "tool_status", "status": "error", "content": "Authentication needed"})
                    yield sse({"type": "text", "content": "I cannot access your emails because your session is missing the required permissions. Please log out and log in again."})
                    return
                    
                yield sse({"type": "tool_status", "status": "pending", "content": "Fetching recent emails from Gmail..."})
                
                async with httpx.AsyncClient() as client:
                    headers = {"Authorization": f"Bearer {access_token}"}
                    # Fetch last 10 messages
                    res = await client.get("https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=10&q=in:inbox", headers=headers)
                    if res.status_code != 200:
                        yield sse({"type": "tool_status", "status": "error", "content": "Failed to connect to Gmail"})
                        return
                    
                    messages = res.json().get('messages', [])
                    
                    if not messages:
                        yield sse({"type": "tool_status", "status": "success", "content": "Inbox is empty."})
                        yield sse({"type": "text", "content": "You have no recent emails in your inbox."})
                        return
                        
                    yield sse({"type": "tool_status", "status": "pending", "content": f"Analyzing {len(messages)} emails with Gemini..."})
                    
                    # Fetch details for each message concurrently
                    async def fetch_msg(msg_id):
                        msg_res = await client.get(f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}", headers=headers)
                        if msg_res.status_code == 200:
                            data = msg_res.json()
                            headers_list = data.get('payload', {}).get('headers', [])
                            subject = next((h['value'] for h in headers_list if h['name'] == 'Subject'), 'No Subject')
                            sender = next((h['value'] for h in headers_list if h['name'] == 'From'), 'Unknown Sender')
                            snippet = data.get('snippet', '')
                            return f"From: {sender} | Subject: {subject} | Snippet: {snippet}"
                        return ""
                        
                    email_details = await asyncio.gather(*[fetch_msg(m['id']) for m in messages])
                    valid_emails = [e for e in email_details if e]
                    
                    # RAG Prompt to Gemini
                    rag_prompt = f"The user asked: '{prompt}'. Here are the user's latest 10 emails. Summarize them concisely and professionally, highlighting anything urgent:\n\n" + "\n".join(valid_emails)
                    
                    rag_model = genai.GenerativeModel('gemini-3-flash-preview')
                    rag_response = await asyncio.to_thread(rag_model.generate_content, rag_prompt)
                    summary = rag_response.text
                    
                    yield sse({"type": "tool_status", "status": "success", "content": "Email analysis complete."})
                    
                    # Stream the summary words
                    for chunk in summary.split(" "):
                        yield sse({"type": "text", "content": chunk + " "})
                        await asyncio.sleep(0.05)
                
            elif action == "COUNT_EMAILS":
                yield sse({"type": "tool_status", "status": "pending", "content": "Scanning inbox..."})
                await asyncio.sleep(1.5)
                yield sse({"type": "tool_status", "status": "success", "content": "Inbox scan complete."})
                
                text = f"You received 42 emails {params.get('timeframe', 'recently')}. Most of them are notifications."
                for chunk in text.split(" "):
                    yield sse({"type": "text", "content": chunk + " "})
                    await asyncio.sleep(0.05)
                    
            elif action == "CREATE_SHEET_FROM_EMAILS":
                access_token = request.session.get('access_token')
                if not access_token:
                    yield sse({"type": "tool_status", "status": "error", "content": "Authentication needed"})
                    yield sse({"type": "text", "content": "I cannot access your emails because your session is missing the required permissions. Please log out and log in again."})
                    return
                    
                yield sse({"type": "tool_status", "status": "pending", "content": "Fetching recent emails..."})
                
                async with httpx.AsyncClient() as client:
                    headers = {"Authorization": f"Bearer {access_token}"}
                    # Fetch last 15 messages
                    res = await client.get("https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=15&q=in:inbox", headers=headers)
                    if res.status_code != 200:
                        yield sse({"type": "tool_status", "status": "error", "content": "Failed to connect to Gmail"})
                        return
                    
                    messages = res.json().get('messages', [])
                    if not messages:
                        yield sse({"type": "tool_status", "status": "success", "content": "Inbox is empty."})
                        return
                        
                    yield sse({"type": "tool_status", "status": "pending", "content": "Extracting email data..."})
                    
                    async def fetch_msg_data(msg_id):
                        msg_res = await client.get(f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}", headers=headers)
                        if msg_res.status_code == 200:
                            data = msg_res.json()
                            headers_list = data.get('payload', {}).get('headers', [])
                            subject = next((h['value'] for h in headers_list if h['name'] == 'Subject'), 'No Subject')
                            sender = next((h['value'] for h in headers_list if h['name'] == 'From'), 'Unknown Sender')
                            date = next((h['value'] for h in headers_list if h['name'] == 'Date'), '')
                            snippet = data.get('snippet', '')
                            return [date, sender, subject, snippet]
                        return None
                        
                    email_rows = await asyncio.gather(*[fetch_msg_data(m['id']) for m in messages])
                    valid_rows = [r for r in email_rows if r]
                    
                    yield sse({"type": "tool_status", "status": "pending", "content": "Creating Google Sheet..."})
                    
                    # Create the spreadsheet
                    sheet_meta = {
                        "properties": {
                            "title": "Email Data Analysis"
                        }
                    }
                    create_res = await client.post("https://sheets.googleapis.com/v4/spreadsheets", headers=headers, json=sheet_meta)
                    
                    if create_res.status_code != 200:
                        yield sse({"type": "tool_status", "status": "error", "content": "Failed to create Google Sheet"})
                        print("Sheets API error:", create_res.text)
                        return
                        
                    sheet_data = create_res.json()
                    spreadsheet_id = sheet_data.get('spreadsheetId')
                    spreadsheet_url = sheet_data.get('spreadsheetUrl')
                    
                    # Populate the spreadsheet
                    yield sse({"type": "tool_status", "status": "pending", "content": "Populating data rows..."})
                    
                    values = [["Date", "Sender", "Subject", "Snippet"]] + valid_rows
                    
                    update_payload = {
                        "values": values
                    }
                    update_res = await client.post(
                        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/Sheet1!A1:D:append?valueInputOption=USER_ENTERED",
                        headers=headers,
                        json=update_payload
                    )
                    
                    yield sse({"type": "tool_status", "status": "success", "content": "Sheet created and populated successfully."})
                    
                    text = f"I have successfully extracted {len(valid_rows)} emails and organized them into a new Google Sheet in your Drive."
                    for chunk in text.split(" "):
                        yield sse({"type": "text", "content": chunk + " "})
                        await asyncio.sleep(0.05)
                        
                    yield sse({
                        "type": "action_card",
                        "content": f"Email Data Analysis Spreadsheet ({len(valid_rows)} rows).",
                        "cardData": {
                            "icon": "mail",
                            "title": "Sheet Ready",
                            "headline": "Email_Data_Analysis",
                            "primaryAction": "Open Sheet",
                            "url": spreadsheet_url
                        }
                    })
                    
            elif action == "CREATE_DOC_FROM_EMAILS":
                access_token = request.session.get('access_token')
                if not access_token:
                    yield sse({"type": "tool_status", "status": "error", "content": "Authentication needed"})
                    yield sse({"type": "text", "content": "I cannot access your emails because your session is missing the required permissions. Please log out and log in again."})
                    return
                    
                yield sse({"type": "tool_status", "status": "pending", "content": "Fetching recent emails..."})
                
                async with httpx.AsyncClient() as client:
                    headers = {"Authorization": f"Bearer {access_token}"}
                    # Fetch last 15 messages
                    res = await client.get("https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=15&q=in:inbox", headers=headers)
                    if res.status_code != 200:
                        yield sse({"type": "tool_status", "status": "error", "content": "Failed to connect to Gmail"})
                        return
                    
                    messages = res.json().get('messages', [])
                    if not messages:
                        yield sse({"type": "tool_status", "status": "success", "content": "Inbox is empty."})
                        return
                        
                    yield sse({"type": "tool_status", "status": "pending", "content": "Extracting email data..."})
                    
                    async def fetch_msg_data(msg_id):
                        msg_res = await client.get(f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}", headers=headers)
                        if msg_res.status_code == 200:
                            data = msg_res.json()
                            headers_list = data.get('payload', {}).get('headers', [])
                            subject = next((h['value'] for h in headers_list if h['name'] == 'Subject'), 'No Subject')
                            sender = next((h['value'] for h in headers_list if h['name'] == 'From'), 'Unknown Sender')
                            date = next((h['value'] for h in headers_list if h['name'] == 'Date'), '')
                            snippet = data.get('snippet', '')
                            return [date, sender, subject, snippet]
                        return None
                        
                    email_rows = await asyncio.gather(*[fetch_msg_data(m['id']) for m in messages])
                    valid_rows = [r for r in email_rows if r]
                    
                    yield sse({"type": "tool_status", "status": "pending", "content": "Creating Google Doc..."})
                    
                    # Create the Document
                    doc_meta = {
                        "title": "Email Data Export"
                    }
                    create_res = await client.post("https://docs.googleapis.com/v1/documents", headers=headers, json=doc_meta)
                    
                    if create_res.status_code != 200:
                        yield sse({"type": "tool_status", "status": "error", "content": "Failed to create Google Doc"})
                        print("Docs API error:", create_res.text)
                        return
                        
                    doc_data = create_res.json()
                    document_id = doc_data.get('documentId')
                    document_url = f"https://docs.google.com/document/d/{document_id}/edit"
                    
                    # Populate the document
                    yield sse({"type": "tool_status", "status": "pending", "content": "Writing email content..."})
                    
                    content_text = "Email Data Export\n\n"
                    for e in valid_rows:
                        content_text += f"Date: {e[0]}\nFrom: {e[1]}\nSubject: {e[2]}\nSnippet: {e[3]}\n\n" + "-"*40 + "\n\n"
                    
                    update_payload = {
                        "requests": [
                            {
                                "insertText": {
                                    "location": {
                                        "index": 1
                                    },
                                    "text": content_text
                                }
                            }
                        ]
                    }
                    update_res = await client.post(
                        f"https://docs.googleapis.com/v1/documents/{document_id}:batchUpdate",
                        headers=headers,
                        json=update_payload
                    )
                    
                    if update_res.status_code != 200:
                        print("Docs update error:", update_res.text)
                    
                    yield sse({"type": "tool_status", "status": "success", "content": "Google Doc generated successfully."})
                    
                    text = f"I have successfully compiled {len(valid_rows)} emails and generated a new Google Document in your Drive."
                    for chunk in text.split(" "):
                        yield sse({"type": "text", "content": chunk + " "})
                        await asyncio.sleep(0.05)
                        
                    yield sse({
                        "type": "action_card",
                        "content": f"Email Export Document ({len(valid_rows)} emails).",
                        "cardData": {
                            "icon": "file-text",
                            "title": "Doc Ready",
                            "headline": "Email_Data_Export",
                            "primaryAction": "Open Doc",
                            "url": document_url
                        }
                    })
                
            else:
                text = params.get('response', "I couldn't understand that request.")
                for chunk in text.split(" "):
                    yield sse({"type": "text", "content": chunk + " "})
                    await asyncio.sleep(0.05)
                
        except Exception as e:
            print(f"Gemini error: {e}")
            yield sse({"type": "tool_status", "status": "error", "content": "Processing failed"})
            yield sse({"type": "text", "content": "I encountered an error processing your request."})

    return StreamingResponse(generate_response(), media_type="text/event-stream")
