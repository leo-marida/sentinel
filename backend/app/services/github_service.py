"""
Fetch source files from a GitHub repository via PyGitHub.
Only fetches text files under 1MB. Caps at max_files to avoid token overflow.
Sync PyGitHub calls are wrapped in asyncio.to_thread to avoid blocking the event loop.
"""
import asyncio
import base64
import logging
from typing import Optional
from urllib.parse import urlparse

import requests.exceptions
import urllib3.exceptions
from github import Github, GithubException
from github.Repository import Repository

from app.config import settings

logger = logging.getLogger(__name__)

SCANNABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb",
    ".php", ".cs", ".cpp", ".c", ".h", ".rs", ".swift", ".kt",
    ".yaml", ".yml", ".json", ".toml", ".tf", ".sh", ".bash",
}

MAX_FILE_SIZE = 500_000


def _parse_repo_url(repo_url: str) -> tuple[str, str]:
    path = urlparse(repo_url).path.strip("/")
    parts = path.split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse repo from URL: {repo_url}")
    return parts[0], parts[1]


def _get_file_content(repo: Repository, path: str) -> Optional[str]:
    try:
        file_obj = repo.get_contents(path)
        if isinstance(file_obj, list):
            return None
        if file_obj.size > MAX_FILE_SIZE:
            return None
        if file_obj.encoding == "base64" and file_obj.content:
            return base64.b64decode(file_obj.content).decode("utf-8", errors="replace")
        return None
    except (GithubException, UnicodeDecodeError, urllib3.exceptions.HTTPError, requests.exceptions.RequestException) as e:
        logger.warning("Skipping %s: %s", path, e)
        return None


def _fetch_sync(repo_url: str, max_files: int) -> list[dict]:
    """Synchronous file fetch — run via asyncio.to_thread."""
    owner, repo_name = _parse_repo_url(repo_url)

    gh = Github(settings.GITHUB_TOKEN)
    try:
        repo = gh.get_repo(f"{owner}/{repo_name}")
    except (GithubException, urllib3.exceptions.HTTPError, requests.exceptions.RequestException) as e:
        raise ValueError(f"Cannot access repo {owner}/{repo_name}: {e}") from e

    files: list[dict] = []
    stack: list[str] = [""]

    while stack and len(files) < max_files:
        dir_path = stack.pop()
        try:
            contents = repo.get_contents(dir_path)
        except (GithubException, urllib3.exceptions.HTTPError, requests.exceptions.RequestException) as e:
            logger.warning("Cannot read directory %s: %s", dir_path, e)
            continue

        if not isinstance(contents, list):
            contents = [contents]

        for item in contents:
            if len(files) >= max_files:
                break
            if item.type == "dir":
                stack.append(item.path)
            elif item.type == "file":
                ext = "." + item.name.rsplit(".", 1)[-1] if "." in item.name else ""
                if ext.lower() not in SCANNABLE_EXTENSIONS:
                    continue
                content = _get_file_content(repo, item.path)
                if content:
                    files.append({"path": item.path, "content": content})

    logger.info("Fetched %d files from %s/%s", len(files), owner, repo_name)
    gh.close()
    return files


async def fetch_repo_files(repo_url: str, max_files: int = 100) -> list[dict]:
    """Async wrapper — runs blocking PyGitHub I/O in a thread pool."""
    return await asyncio.to_thread(_fetch_sync, repo_url, max_files)