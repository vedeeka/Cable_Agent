from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages


class AgentState(TypedDict):

    messages: Annotated[list, add_messages]

    name: str
    email: str

    access_token: str
    refresh_token: str | None

    context: str

    response: str
    latest_email: str

    latest_calendar: str

    latest_drive: str

    documents_synced: int

    chunks_created: int