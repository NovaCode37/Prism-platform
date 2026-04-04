import hmac
import os
import re
from typing import Optional

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "20")) * 1024 * 1024
MAX_TARGET_LEN   = 512

API_KEY: Optional[str] = os.getenv("API_KEY", "").strip() or None

limiter = Limiter(key_func=get_remote_address, default_limits=["200/day", "60/hour"])


async def require_api_key(request: Request) -> None:
    if not API_KEY:
        return
    key = (
        request.headers.get("X-API-Key")
        or request.query_params.get("api_key")
    )
    if not key or not hmac.compare_digest(key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Pass X-API-Key header.",
        )


def validate_target(target: str) -> str:
    target = target.strip()
    if not target:
        raise HTTPException(status_code=400, detail="Target is empty.")
    if len(target) > MAX_TARGET_LEN:
        raise HTTPException(status_code=400, detail="Target too long.")
    forbidden = re.compile(r"[;\|`$<>{}]")
    if forbidden.search(target):
        raise HTTPException(status_code=400, detail="Target contains forbidden characters.")
    return target


async def check_upload_size(request: Request) -> None:
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {MAX_UPLOAD_BYTES // (1024*1024)} MB allowed.",
        )


def get_allowed_origins() -> list:
    raw = os.getenv("ALLOWED_ORIGINS", "")
    if not raw or raw.strip() == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]
