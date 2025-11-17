# c:\Users\Azamat\Documents\telegram bot\storage.py
import json
from typing import Dict, List, Optional, Any

USERS_FILE = "users.json"

def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a user's data from the JSON file."""
    try:
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
        return users.get(str(user_id))
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def save_user(user_id: int, data: Dict[str, Any]) -> None:
    """Saves or updates a user's data in the JSON file."""
    try:
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        users = {}

    users[str(user_id)] = data

    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def set_user_field(user_id: int, field: str, value: Any) -> None:
    """Sets a specific field for a user."""
    user_data = get_user(user_id)
    if user_data:
        user_data[field] = value
        save_user(user_id, user_data)

def get_all_users() -> List[Dict[str, Any]]:
    """Retriedves all users from the JSON file."""
    try:
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
        return list(users.values())
    except (FileNotFoundError, json.JSONDecodeError):
        return []
