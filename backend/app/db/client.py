import logging
import threading
import time

import httpx
from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions

from app.config import settings

logger = logging.getLogger(__name__)

_local = threading.local()

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 1.0  # doubles each attempt
POSTGREST_TIMEOUT_SECONDS = 20  # default is 120s; fail fast so the retry wrapper can act


def _add_retry(session: httpx.Client) -> None:
    """
    Wrap the client's request method so transient network blips (TLS handshake
    timeouts, dropped connections) don't crash a request or silently kill a
    pipeline step. Retries only httpx.TransportError (connect/read/write/protocol
    failures) — never retries on a successful response, even an HTTP error one.
    """
    original_request = session.request

    def request_with_retry(method, url, **kwargs):
        for attempt in range(RETRY_ATTEMPTS + 1):
            try:
                return original_request(method, url, **kwargs)
            except httpx.TransportError as e:
                if attempt == RETRY_ATTEMPTS:
                    raise
                delay = RETRY_BACKOFF_SECONDS * (2 ** attempt)
                logger.warning(
                    "[db] %s %s failed (%s), retrying in %.1fs (attempt %d/%d)",
                    method, url, e, delay, attempt + 1, RETRY_ATTEMPTS,
                )
                time.sleep(delay)

    session.request = request_with_retry


def get_supabase() -> Client:
    """One Client per OS thread, with retry-on-transient-network-error wrapping."""
    if not hasattr(_local, "client"):
        options = ClientOptions(postgrest_client_timeout=POSTGREST_TIMEOUT_SECONDS)
        client = create_client(
            settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY, options=options
        )
        _add_retry(client.postgrest.session)
        _local.client = client
    return _local.client


async def init_db() -> None:
    """Verify Supabase connectivity on startup."""
    client = get_supabase()
    client.table("scans").select("id").limit(1).execute()