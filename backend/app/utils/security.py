"""
Security utilities: GitHub URL validation and in-memory rate limiting.
Rate limit: max 5 scans per IP per hour (Section 10 requirement).
"""
import time
from collections import defaultdict
from urllib.parse import urlparse

from fastapi import HTTPException, Request

_rate_limit_store: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_MAX = 5
_RATE_LIMIT_WINDOW = 3600  # seconds


def validate_github_url(url: str) -> str:
    """Reject anything that is not a github.com repo URL."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="URL must use http or https")
    if parsed.netloc not in ("github.com", "www.github.com"):
        raise HTTPException(status_code=400, detail="Only github.com URLs are supported")
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="URL must point to a GitHub repository (owner/repo)")
    return url


def check_rate_limit(request: Request) -> None:
    """Raise 429 if the IP has exceeded the scan rate limit."""
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - _RATE_LIMIT_WINDOW
    _rate_limit_store[ip] = [t for t in _rate_limit_store[ip] if t > window_start]
    if len(_rate_limit_store[ip]) >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {_RATE_LIMIT_MAX} scans per hour",
        )
    _rate_limit_store[ip].append(now)