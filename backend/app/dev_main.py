"""Independent development entry point for PayPause modules (Bhuvan).

Runs standalone for local testing and demonstration.
Includes all Bhuvan assigned modules:
- Flagsmith Experimentation (/api/experiments)
- Payment Management (/api/payments)
- Recurring Payments / Subscriptions (/api/subscriptions)
- Recovery Desk (/api/recovery)

To run:
    uvicorn backend.app.dev_main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import get_settings
from backend.app.api.experiments import router as experiments_router
from backend.app.api.payments import router as payments_router
from backend.app.api.subscriptions import router as subscriptions_router
from backend.app.api.recovery import router as recovery_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "PayPause Independent Backend Modules developed by Bhuvan.\n\n"
        "Features:\n"
        "- **Flagsmith Experimentation**: A/B evaluation of payment intelligence experiences.\n"
        "- **Payment Management**: Transaction records, filtering, and refund tracking.\n"
        "- **Subscriptions**: Recurring payment management and leap-year/month-end forecast.\n"
        "- **Recovery Desk**: Incident logging, evidence checklists, and statutory complaint drafting."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for local testing and demonstration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Bhuvan's API routers
app.include_router(experiments_router)
app.include_router(payments_router)
app.include_router(subscriptions_router)
app.include_router(recovery_router)


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint indicating active independent backend status."""
    return {
        "status": "healthy",
        "app_env": settings.app_env,
        "flagsmith_configured": bool(settings.flagsmith_environment_key),
        "modules_active": [
            "experiments",
            "payments",
            "subscriptions",
            "recovery",
        ],
    }


@app.get("/", tags=["Health"])
def root():
    """Landing route with links to API documentation."""
    return {
        "message": "PayPause Independent Backend is active.",
        "documentation": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.dev_main:app", host="127.0.0.1", port=8000, reload=True)
