import logging
import time
from uuid import uuid4

from fastapi import Request

logger = logging.getLogger("paypause.http")


async def request_middleware(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id

    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        logger.info(
            "HTTP request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "request_id": request_id,
            },
        )

        return response

    except Exception:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        logger.exception(
            "HTTP request failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
                "request_id": request_id,
            },
        )
        raise
