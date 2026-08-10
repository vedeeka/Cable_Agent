from typing import TypedDict, Optional, List, Dict, Any

class AgentState(TypedDict):
    # Keep your existing state keys ...
    messages: List[Any]
    user_id: str
    name: str
    email: str
    access_token: str
    refresh_token: Optional[str]
    integrations: Dict[str, bool]
    query: str
    intent: str
    plan: List[Any]
    next_step: int
    context: str
    tool_results: Dict[str, Any]
    response: str
    
    # Add these keys to prevent LangGraph from stripping them:
    latest_email: Optional[str]
    latest_calendar: Optional[str]
    latest_drive: Optional[str]
    latest_sheets: Optional[str]
    documents_synced: Optional[int]
    chunks_created: Optional[int]