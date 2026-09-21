"""Local customer accounts. Email or phone, password hashed on disk."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import threading
from pathlib import Path

_LOCK = threading.Lock()
_STORE = Path(__file__).resolve().parents[2] / "data" / "accounts.json"
_ITERATIONS = 200_000


def _load() -> dict:
    if not _STORE.exists():
        return {"users": [], "tokens": {}}
    try:
        data = json.loads(_STORE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"users": [], "tokens": {}}
    data.setdefault("users", [])
    data.setdefault("tokens", {})
    return data


def _save(data: dict) -> None:
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def normalize_identifier(raw: str) -> tuple[str, str]:
    text = " ".join(raw.strip().split())
    if "@" in text:
        email = text.lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("Enter a valid email.")
        return "email", email
    phone = re.sub(r"\D", "", text)
    if len(phone) < 8:
        raise ValueError("Enter an email or a phone number.")
    return "phone", phone


def _hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), _ITERATIONS)
    return digest.hex()


def _public(user: dict) -> dict:
    ident = user["identifier"]
    if user["kind"] == "email":
        name = ident.split("@", 1)[0]
    else:
        name = ident[-4:].rjust(len(ident), "•")
    return {"id": user["id"], "identifier": ident, "kind": user["kind"], "name": name}


def register(identifier: str, password: str) -> dict:
    kind, ident = normalize_identifier(identifier)
    if len(password) < 8:
        raise ValueError("Password needs at least 8 characters.")
    with _LOCK:
        data = _load()
        if any(user["identifier"] == ident for user in data["users"]):
            raise ValueError("An account with that email or phone already exists.")
        salt = secrets.token_hex(16)
        user = {
            "id": secrets.token_hex(8),
            "identifier": ident,
            "kind": kind,
            "salt": salt,
            "password_hash": _hash_password(password, salt),
        }
        data["users"].append(user)
        token = secrets.token_urlsafe(32)
        data["tokens"][token] = user["id"]
        _save(data)
        return {"token": token, "user": _public(user)}


def login(identifier: str, password: str) -> dict:
    kind, ident = normalize_identifier(identifier)
    del kind
    with _LOCK:
        data = _load()
        user = next((item for item in data["users"] if item["identifier"] == ident), None)
        if user is None or _hash_password(password, user["salt"]) != user["password_hash"]:
            raise ValueError("Email, phone, or password is wrong.")
        token = secrets.token_urlsafe(32)
        data["tokens"][token] = user["id"]
        _save(data)
        return {"token": token, "user": _public(user)}


def user_for_token(token: str) -> dict | None:
    if not token:
        return None
    with _LOCK:
        data = _load()
        user_id = data["tokens"].get(token)
        if not user_id:
            return None
        user = next((item for item in data["users"] if item["id"] == user_id), None)
        return _public(user) if user else None


def logout(token: str) -> None:
    with _LOCK:
        data = _load()
        data["tokens"].pop(token, None)
        _save(data)
