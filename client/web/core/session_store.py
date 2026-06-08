# client/web/core/session_store.py

# Structure par user_session_id :
# {
#   "mcp_session_id": str,
#   "db_type":        str,
#   "messages":       list,
#   "tools":          list,
# }

_store: dict[str, dict] = {}

def create(user_session_id: str, data: dict):
    _store[user_session_id] = data

def get(user_session_id: str) -> dict | None:
    return _store.get(user_session_id)

def delete(user_session_id: str):
    _store.pop(user_session_id, None)

def reset_messages(user_session_id: str):
    session = _store.get(user_session_id)
    if session:
        sys_msg = session["messages"][0]  # garde le sys prompt
        session["messages"] = [sys_msg]

def count() -> int:
    return len(_store)