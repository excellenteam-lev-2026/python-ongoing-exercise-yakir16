from __future__ import annotations
import requests
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

@dataclass
class Status:
    status: str
    filename: str | None
    upload_time: datetime | None
    finish_time: datetime | None
    explanation: list | dict | None
    error_message: str | None

    def is_done(self):
        return self.status == "done"


class GeminiExplainerClient:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url.rstrip("/")

    def upload(self, file_path: str, email: str = None) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Local file not found: {path}")
        
        url = f"{self.base_url}/upload"
        with open(path, "rb") as f:
            files = {"file": (path.name, f)}
            data = {"email": email} if email else None
            response = requests.post(url, files=files, data=data)
        
        if not response.ok:
            raise requests.HTTPError(f"Upload failed: {response.text}")
        
        return response.json()["uid"]

    def status(self, uid: str = None, filename: str = None, email: str = None) -> Status:
        url = f"{self.base_url}/status"
        params = {}
        if uid:
            url += f"/{uid}"
        else:
            params = {"filename": filename, "email": email}
            
        response = requests.get(url, params=params)
        if not response.ok:
            raise requests.HTTPError(f"Status check failed: {response.text}")
        data = response.json()
        def parse_dt(dt_str):
            return datetime.fromisoformat(dt_str) if dt_str else None
        return Status(
            status=data["status"],
            filename=data["filename"],
            upload_time=parse_dt(data["upload_time"]),
            finish_time=parse_dt(data["finish_time"]),
            explanation=data.get("explanation"),
            error_message=data.get("error_message")
        )