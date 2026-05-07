import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("feature_analytics")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        latency_ms = round((time.monotonic() - start) * 1000, 2)

        cache_status = response.headers.get("X-Cache", "MISS")

        logger.info(
            "%s %s | %s | %sms | client=%s",
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
            request.client.host if request.client else "unknown",
        )

        response.headers["X-Response-Time-Ms"] = str(latency_ms)
        return response
