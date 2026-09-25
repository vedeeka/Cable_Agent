# Cable Agent — Enterprise AI OS

> **An intelligent, agentic operating system for the enterprise** — powered by LangGraph, Gemini, and Google Workspace APIs. Cable Agent syncs your Google Workspace (Gmail, Calendar, Drive, Docs, Sheets) into a unified vector knowledge base and exposes a conversational AI layer ("Aeryn") that can reason, plan, and act on your behalf.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Variables](#environment-variables)
  - [Running with Docker (Database)](#running-with-docker-database)
  - [Running the Backend (Modern)](#running-the-backend-modern)
  - [Running the Legacy Agent](#running-the-legacy-agent)
- [API Reference](#api-reference)
- [Agent Architecture (LangGraph)](#agent-architecture-langgraph)
- [Legacy vs Modern Backend](#legacy-vs-modern-backend)

---

## Overview

Cable Agent is an **Enterprise AI Operating System** that:

1. **Authenticates** users via Google OAuth 2.0 (with offline access for token refresh)
2. **Syncs** the user's entire Google Workspace — emails, calendar events, Drive files, and spreadsheets — into a persistent ChromaDB vector store
3. **Embeds** all content using `BAAI/bge-small-en-v1.5` (SentenceTransformers) for semantic search
4. **Exposes** a FastAPI backend with REST + Server-Sent Events (SSE) streaming endpoints
5. **Powers** "Aeryn" — an AI assistant backed by Google Gemini that classifies user intent and executes actions (send email, schedule meetings, summarize, etc.)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│                     http://localhost:3000                    │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST / SSE
┌──────────────────────────▼──────────────────────────────────┐
│                   FastAPI Backend                            │
│               http://localhost:8000                          │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Auth (OAuth) │  │ Chat (Aeryn) │  │  Dashboard API   │   │
│  │  /api/v1/   │  │ /api/v1/chat │  │ /api/dashboard   │   │
│  │  auth/      │  │   /stream    │  │                  │   │
│  └─────────────┘  └──────┬───────┘  └──────────────────┘   │
│                          │ Gemini                            │
│                   ┌──────▼───────┐                          │
│                   │  Google      │                          │
│                   │  Gemini API  │                          │
│                   └──────────────┘                          │
└──────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              LangGraph Agent (legacy/)                       │
│                                                              │
│  startup_node → welcome_node → sync_everything_node → END   │
│                                                              │
│  Google APIs: Gmail, Calendar, Drive, Sheets                │
│  Vector Store: ChromaDB (./vectordb)                        │
│  Embeddings: BAAI/bge-small-en-v1.5                        │
└──────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   PostgreSQL (Docker)                        │
│              Organizations, Users, Sessions                  │
└──────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
Cable_Agent/
├── auth.py                        # (stub) top-level auth module
├── docker-compose.yml             # PostgreSQL service
├── .env                           # root env vars
│
├── backend/                       # Modern FastAPI backend
│   ├── requirements.txt
│   └── app/
│       ├── main.py                # App entrypoint, routers, dashboard API
│       ├── config.py              # Pydantic settings (env-driven)
│       ├── api/
│       │   ├── chat.py            # Aeryn chat w/ Gemini + SSE streaming
│       │   ├── execute.py         # Tool execution endpoint
│       │   ├── organizations.py   # Org management
│       │   └── users.py           # User management
│       ├── database/              # SQLAlchemy models & session
│       ├── security/
│       │   └── auth.py            # Google OAuth flow
│       └── alembic/               # DB migrations
│
└── legacy/                        # Original LangGraph-based agent
    ├── app.py                     # FastAPI app w/ Google OAuth + graph
    ├── graph.py                   # LangGraph StateGraph definition
    ├── nodes.py                   # Agent nodes (startup, welcome, sync)
    ├── state.py                   # AgentState TypedDict
    ├── requirements.txt
    └── Tools/
        ├── GitHubToolkit/
        ├── GoogleToolkit/
        ├── JiraToolkit/
        ├── NotionToolkit/
        ├── SlackToolkit/
        ├── initialize_llm/
        └── summarization/
            └── summarizer.py      # AI summarization node
```

---

## Features

| Feature | Description |
|---|---|
| 🔐 **Google OAuth 2.0** | Offline access with refresh tokens; session-based authentication |
| 📬 **Gmail Sync** | Fetches last 20 inbox messages, stores snippets in vector DB |
| 📅 **Calendar Sync** | Syncs upcoming events (summary, start time, description) |
| 📁 **Drive Sync** | Indexes all Drive file names and MIME types |
| 📊 **Sheets Sync** | Reads up to 10 tabs per spreadsheet, handles A:Z range with retry logic |
| 🧠 **Vector Knowledge Base** | ChromaDB + `BAAI/bge-small-en-v1.5` embeddings with per-user metadata |
| 💬 **Aeryn AI Chat** | Gemini-powered intent classifier + SSE streaming responses |
| 🗂️ **Multi-tenant Backend** | PostgreSQL with organizations and users tables (Alembic migrations) |
| 🐳 **Docker Support** | One-command PostgreSQL spin-up via `docker-compose` |
| 📡 **SSE Streaming** | Real-time tool status and text response streaming |

### Supported Chat Actions (Aeryn)

- `SEND_EMAIL` — Compose and send emails
- `SCHEDULE_MEETING` — Create calendar events
- `COUNT_EMAILS` — Count emails by timeframe
- `CREATE_SHEET_FROM_EMAILS` — Generate Google Sheets from email data
- `CREATE_DOC_FROM_EMAILS` — Generate Google Docs from email data
- `SUMMARIZE_EMAILS` — Intelligent email summarization
- `SUMMARIZE_CALENDAR` — Calendar event summarization
- `GENERAL_CHAT` — Open-ended conversation

---

## Tech Stack

### Backend
- **[FastAPI](https://fastapi.tiangolo.com/)** — Async REST API framework
- **[LangGraph](https://langchain-ai.github.io/langgraph/)** — Stateful agent graph orchestration
- **[LangChain](https://www.langchain.com/)** — LLM tooling and text splitters
- **[Google Gemini API](https://ai.google.dev/)** — LLM for intent classification and responses
- **[ChromaDB](https://www.trychroma.com/)** — Persistent local vector store
- **[SentenceTransformers](https://www.sbert.net/)** — `BAAI/bge-small-en-v1.5` embeddings
- **[Authlib](https://authlib.org/)** — OAuth 2.0 client
- **[SQLAlchemy](https://www.sqlalchemy.org/) + [Alembic](https://alembic.sqlalchemy.org/)** — ORM and migrations
- **[PostgreSQL](https://www.postgresql.org/)** — Relational database

### Google APIs
- Gmail API (v1)
- Google Calendar API (v3)
- Google Drive API (v3)
- Google Sheets API (v4)
- Google Docs API (v1)

---

## Getting Started

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- A Google Cloud project with OAuth 2.0 credentials and the following APIs enabled:
  - Gmail API
  - Google Calendar API
  - Google Drive API
  - Google Sheets API
  - Google Docs API

### Environment Variables

Create a `.env` file in the **`backend/`** directory (and optionally in `legacy/`):

```env
# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# App
SECRET_KEY=your_secret_key_here

# Database (must match docker-compose.yml)
POSTGRES_SERVER=localhost
POSTGRES_USER=enterprise_user
POSTGRES_PASSWORD=enterprise_password
POSTGRES_DB=enterprise_db
POSTGRES_PORT=5432

# AI
GEMINI_API_KEY=your_gemini_api_key
```

### Running with Docker (Database)

```bash
# Start the PostgreSQL database
docker-compose up -d

# Verify it is running
docker-compose ps
```

### Running the Backend (Modern)

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --host localhost --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

### Running the Legacy Agent

The legacy agent includes the full LangGraph pipeline with Google Workspace sync:

```bash
cd legacy

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app:app --reload --host localhost --port 8000
```

---

## API Reference

### Auth Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/login` | Redirect to Google OAuth consent screen |
| `GET` | `/authorize` | OAuth callback; sets session cookie |
| `GET` | `/api/me` | Returns the current authenticated user |
| `GET/POST` | `/logout` or `/api/logout` | Clears the session |

### Dashboard & Data Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/dashboard` | Returns latest email, calendar, drive, and sheets info |
| `POST` | `/api/sync` | Manually trigger Google Workspace sync (pass tokens in body) |
| `GET` | `/api/summary` | Generate an AI summary of the user's workspace |

**Manual Sync request body:**
```json
{
  "email": "user@example.com",
  "access_token": "ya29...",
  "refresh_token": "1//...",
  "name": "Jane Doe"
}
```

### Chat Endpoints (Modern Backend)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/chat/stream` | SSE streaming chat with Aeryn (Gemini-powered) |

**Request body:**
```json
{ "prompt": "Summarize my last 5 emails" }
```

**SSE Event types:**
```json
{ "type": "tool_status", "status": "pending|success|error", "content": "..." }
{ "type": "text", "content": "word " }
```

### Organization & User Endpoints (Modern Backend)

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `/api/v1/organizations/` | List or create organizations |
| `GET/POST` | `/api/v1/users/` | List or create users |

---

## Agent Architecture (LangGraph)

The legacy agent uses a **linear StateGraph** with three nodes:

```
[startup_node] → [welcome_node] → [sync_everything_node] → END
```

| Node | Responsibility |
|---|---|
| `startup_node` | Logs the connected user; initializes context string |
| `welcome_node` | Returns a welcome message to the user |
| `sync_everything_node` | Fetches and embeds all Google Workspace data into ChromaDB |

**State** (`AgentState`) carries:
- User identity (`user_id`, `name`, `email`)
- OAuth tokens (`access_token`, `refresh_token`)
- Integration flags (`gmail`, `calendar`, `drive`, `docs`, `sheets`)
- Agent reasoning (`query`, `intent`, `plan`, `context`, `tool_results`, `response`)
- Sync results (`latest_email`, `latest_calendar`, `latest_drive`, `latest_sheets`, `documents_synced`, `chunks_created`)

The graph uses **`InMemorySaver`** as a checkpointer, keyed by `thread_id` (the user's Google sub or email), enabling per-user persistent memory across requests.

---

## Legacy vs Modern Backend

| Aspect | `legacy/` | `backend/` |
|---|---|---|
| **Framework** | FastAPI + LangGraph | FastAPI (modular routers) |
| **Auth** | Session-based Google OAuth | Session-based Google OAuth |
| **AI** | LangGraph agent + Google Gemini | Gemini directly (no graph) |
| **Vector DB** | ChromaDB (local) | — |
| **Database** | — | PostgreSQL (via Docker) |
| **Chat** | `/api/chat` (sync) | `/api/v1/chat/stream` (SSE streaming) |
| **Status** | Reference / research | **Active development** |

---

## License

This project is proprietary. All rights reserved.
