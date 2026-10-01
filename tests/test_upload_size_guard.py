import os
os.environ["API_KEYS"] = "testkey"

import pytest
from fastapi.testclient import TestClient

from web.app import app
from web.security import MAX_UPLOAD_BYTES

client = TestClient(app)

def test_metadata_upload_size_guard_no_content_length(monkeypatch):
    monkeypatch.setenv("API_KEYS", "testkey")
    
    large_content = b"0" * (MAX_UPLOAD_BYTES + 1024)
    
    class FakeFile:
        def __init__(self, data):
            self.data = data
            self.pos = 0
            
        def read(self, size=-1):
            if self.pos >= len(self.data):
                return b""
            if size == -1:
                chunk = self.data[self.pos:]
                self.pos = len(self.data)
                return chunk
            chunk = self.data[self.pos:self.pos+size]
            self.pos += size
            return chunk

    files = {"file": ("test.jpg", FakeFile(large_content), "image/jpeg")}
    
    response = client.post(
        "/api/metadata",
        headers={"x-api-key": "testkey"},
        files=files
    )
    
    assert response.status_code == 413
    assert "File too large" in response.json()["detail"]

def test_metadata_upload_invalid_content_length(monkeypatch):
    monkeypatch.setenv("API_KEYS", "testkey")
    
    files = {"file": ("test.jpg", b"small data", "image/jpeg")}
    
    response = client.post(
        "/api/metadata",
        headers={"x-api-key": "testkey", "content-length": "abc"},
        files=files
    )
    
    assert response.status_code == 400
    assert "Invalid Content-Length header" in response.json()["detail"]
