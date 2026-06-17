"""
Run Semgrep (OSS ruleset) and Bandit on fetched repo files.
Blocking subprocess calls are run via asyncio.to_thread to avoid blocking the event loop.
"""
import asyncio
import json
import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

SEMGREP_TIMEOUT = 60
BANDIT_TIMEOUT = 60


def _write_files_to_temp(files: list[dict]) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="sentinel_scan_"))
    for f in files:
        dest = tmp / f["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(f["content"], encoding="utf-8", errors="replace")
    return tmp


def _run_semgrep(scan_dir: Path) -> list[dict]:
    try:
        result = subprocess.run(
            ["semgrep", "--config", "auto", "--json", "--quiet", str(scan_dir)],
            capture_output=True,
            text=True,
            timeout=SEMGREP_TIMEOUT,
        )
        if result.stdout:
            data = json.loads(result.stdout)
            findings = data.get("results", [])
            for f in findings:
                try:
                    f["path"] = str(Path(f["path"]).relative_to(scan_dir))
                except ValueError:
                    pass
            logger.info("Semgrep: %d findings", len(findings))
            return findings
    except subprocess.TimeoutExpired:
        logger.warning("Semgrep timed out after %ds", SEMGREP_TIMEOUT)
    except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
        logger.warning("Semgrep error: %s", e)
    return []


def _run_bandit(scan_dir: Path) -> list[dict]:
    py_files = list(scan_dir.rglob("*.py"))
    if not py_files:
        return []
    try:
        result = subprocess.run(
            ["bandit", "-r", str(scan_dir), "-f", "json", "-q"],
            capture_output=True,
            text=True,
            timeout=BANDIT_TIMEOUT,
        )
        output = result.stdout or result.stderr
        if output:
            data = json.loads(output)
            findings = data.get("results", [])
            for f in findings:
                try:
                    f["filename"] = str(Path(f["filename"]).relative_to(scan_dir))
                except ValueError:
                    pass
                f["path"] = f.get("filename", "unknown")
                f["check_id"] = f.get("test_id", "bandit-unknown")
                f["start"] = {"line": f.get("line_number", 0)}
                f["end"] = {"line": f.get("line_number", 0)}
                f["extra"] = {"message": f.get("issue_text", "")}
            logger.info("Bandit: %d findings", len(findings))
            return findings
    except subprocess.TimeoutExpired:
        logger.warning("Bandit timed out after %ds", BANDIT_TIMEOUT)
    except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
        logger.warning("Bandit error: %s", e)
    return []


def _cleanup(scan_dir: Path) -> None:
    import shutil
    try:
        shutil.rmtree(scan_dir)
    except Exception as e:
        logger.warning("Cleanup failed for %s: %s", scan_dir, e)


async def scan_files(files: list[dict]) -> list[dict]:
    """Write files to disk, run Semgrep + Bandit in thread pool, return combined findings."""
    if not files:
        return []

    scan_dir = _write_files_to_temp(files)
    try:
        semgrep_findings, bandit_findings = await asyncio.gather(
            asyncio.to_thread(_run_semgrep, scan_dir),
            asyncio.to_thread(_run_bandit, scan_dir),
        )
        return semgrep_findings + bandit_findings
    finally:
        _cleanup(scan_dir)