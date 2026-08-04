from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import OUTPUTS_DIR, UPLOADS_DIR, USERS_DIR
from .models import UserProfile


def ensure_dirs() -> None:
    USERS_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def user_profile_path(user_id: str) -> Path:
    ensure_dirs()
    return USERS_DIR / f"{user_id}.json"


def load_user_profile(user_id: str) -> UserProfile:
    path = user_profile_path(user_id)
    if not path.exists():
        return UserProfile(user_id=user_id)
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return UserProfile.from_dict(data)


def save_user_profile(profile: UserProfile) -> Path:
    path = user_profile_path(profile.user_id)
    with path.open("w", encoding="utf-8") as file:
        json.dump(profile.to_dict(), file, indent=2)
    return path


def save_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
    return path


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)
