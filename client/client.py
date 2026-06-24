from __future__ import annotations
import requests
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Status:
    status: str
    filename: str | None
    timestamp: datetime | None
    explanation: list | dict | None

    def is_done(self):
        return self.status == "done"


class GeminiExplainerClient:
    def __init__(self, base_url = "http://127.0.0.1:5000"):
        self.base_url = base_url.rstrip("/")

    def upload(self,file_path):
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Local file not found: {path}")
        
        url = f"{self.base_url}/upload"
        with open(path, "rb") as f:
            files = {"file": (path.name, f)}
            response = requests.post(url, files=files)
        
        if not response.ok:
            raise requests.HTTPError(f"Upload failed with status {response.status_code}: {response.text}")
        
        return response.json()["uid"]

    def status(self,uid):
        url = f"{self.base_url}/status/{uid}"
        response = requests.get(url)
        
        if not response.ok:
            raise requests.HTTPError(f"Status check failed with status {response.status_code}: {response.text}")
        data = response.json()
        parsed_time = None
        if data.get("timestamp"):
            try:
                parsed_time = datetime.strptime(data["timestamp"], "%Y%m%d%H%M%S")
            except ValueError:
                parsed_time = None
                
        return Status(
            status=data["status"],
            filename=data["filename"],
            timestamp=parsed_time,
            explanation=data["explanation"]
        )
