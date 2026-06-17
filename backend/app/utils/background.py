"""
Run an async coroutine in a dedicated background thread with its own event loop.

The Supabase Python client is synchronous under the hood (every .execute() call
is a blocking HTTP request). If pipeline coroutines run on FastAPI's main event
loop, those blocking calls freeze the entire server for every other request.
Running the whole pipeline in an isolated thread + loop keeps the main loop free.
"""
import asyncio
import logging
import threading
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


def run_async_in_thread(coro_func: Callable[..., Coroutine[Any, Any, None]], *args: Any) -> None:
    def _target() -> None:
        try:
            asyncio.run(coro_func(*args))
        except Exception:
            logger.error("[background] Uncaught error in background thread", exc_info=True)

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()