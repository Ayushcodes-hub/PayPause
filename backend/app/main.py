import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.exceptions import PayPauseException
from app.core.logging import setup_logging
from app.core.middleware import request_middleware
from app.core.supabase import get_supabase_admin_client
from app.schemas.common import ErrorDetail, ErrorResponse
from app.core.auth import AuthenticatedUser, get_current_user


setup_logging()
logger = logging.getLogger("paypause.application")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("PayPause application starting")
    yield
    logger.info("PayPause application shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Payment safety, financial intelligence and recovery "
        "platform for Indian consumers."
    ),
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

app.middleware("http")(request_middleware)


@app.exception_handler(PayPauseException)
async def paypause_exception_handler(
    request: Request,
    exc: PayPauseException,
):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                details=exc.details,
            )
        ).model_dump(),
        headers={"X-Request-ID": getattr(request.state, "request_id", "")},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    errors = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "code": error["type"],
            "message": error["msg"],
        }
        for error in exc.errors()
    ]

    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="The submitted request data is invalid.",
                details={"errors": errors},
            )
        ).model_dump(),
        headers={"X-Request-ID": getattr(request.state, "request_id", "")},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=ErrorDetail(
                code="HTTP_ERROR",
                message=str(exc.detail),
            )
        ).model_dump(),
        headers={
            **(exc.headers or {}),
            "X-Request-ID": getattr(request.state, "request_id", ""),
        },
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.exception("Unhandled application exception")

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected server error occurred.",
            )
        ).model_dump(),
        headers={"X-Request-ID": getattr(request.state, "request_id", "")},
    )


@app.get("/", tags=["System"])
async def root():
    return {
        "application": settings.APP_NAME,
        "tagline": "Think Before Money Moves.",
        "status": "running",
        "version": settings.APP_VERSION,
    }


@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "healthy",
        "service": "paypause-api",
    }


@app.get("/health/live", tags=["System"])
async def liveness():
    return {
        "status": "alive",
        "service": "paypause-api",
    }


@app.get("/health/ready", tags=["System"])
def readiness():
    database_status = "available"

    try:
        get_supabase_admin_client().table("profiles").select("id").limit(1).execute()
    except Exception:
        logger.exception("Readiness database check failed")
        database_status = "unavailable"

    ai_provider_status = (
        "configured"
        if settings.AI_API_KEY and settings.AI_MODEL
        else "not_configured"
    )

    checks = {
        "application": "initialized",
        "database": database_status,
        "ai_provider": ai_provider_status,
    }

    if database_status != "available":
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "service": "paypause-api",
                "checks": checks,
            },
        )

    return {
        "status": "ready",
        "service": "paypause-api",
        "checks": checks,
    }


@app.get(f"{settings.API_V1_PREFIX}/health", tags=["System"])
async def versioned_health():
    return {
        "success": True,
        "message": "PayPause API v1 is operational.",
        "data": {
            "service": "paypause-api",
            "version": settings.APP_VERSION,
        },
    }

@app.get(
    f"{settings.API_V1_PREFIX}/auth/me",
    tags=["Authentication"],
)
async def get_authenticated_user(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return {
        "success": True,
        "data": {
            "id": str(current_user.id),
            "email": current_user.email,
        },
    }
