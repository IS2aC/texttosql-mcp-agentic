## SCHEMA FILES

│
├── client/
│   ├── web/                         # Client Web Flask
│   │   ├── app.py
│   │   ├── config.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── mcp_client.py        # execute_tool, load_mcp_tools
│   │   │   ├── agent.py             # run_agent, agentic loop
│   │   │   └── session_store.py     # USER_SESSIONS (→ Redis ready)
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── home.py
│   │   │   ├── register.py
│   │   │   └── chat.py
│   │   ├── templates/
│   │   │   ├── home.html
│   │   │   ├── register.html
│   │   │   └── chat.html
│   │   └── static/
│   │
│   └── cli/                         # Client CLI
│       └── main.py