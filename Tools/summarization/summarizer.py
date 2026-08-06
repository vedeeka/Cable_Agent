from state import AgentState
from Tools.db_data.extraction import extraction
from Tools.initialize_llm.initialise_llm import initialise_llm


def summarizer(state: AgentState):
    print("========== SUMMARIZER ==========")

    context = extraction(state)

    documents = "\n\n".join(context.get("documents", []))

    prompt = f"""
You are an Enterprise AI Summarizer.

The following information has been indexed for the user.

==============================
LATEST EMAIL
==============================
{context.get("latest_email")}

==============================
LATEST CALENDAR EVENT
==============================
{context.get("latest_calendar")}

==============================
LATEST DRIVE FILE
==============================
{context.get("latest_drive")}

==============================
LATEST GOOGLE SHEET
==============================
{context.get("latest_sheets")}

==============================
STATISTICS
==============================
Documents Synced:
{context.get("documents_synced")}

Knowledge Chunks:
{context.get("chunks_created")}

==============================
INDEXED DOCUMENTS
==============================
{documents}

==============================
TASK
==============================
Generate a concise enterprise summary including:

1. Latest email activity.
2. Upcoming/latest calendar event.
3. Recently indexed Drive file.
4. Latest Google Sheets information.
5. Overall indexing statistics.
6. Important insights discovered from the indexed documents.

Return only the summary.
Keep it under 250 words.
"""

    response = initialise_llm(prompt)

    print("========== LLM RESPONSE ==========")
    print(response.content)
    return {
    "response": response.content
    }

