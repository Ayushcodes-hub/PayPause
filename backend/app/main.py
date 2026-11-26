from fastapi import FastAPI

app = FastAPI(
    title="PayPause API",
    description=(
        "Payment safety, financial intelligence "
        "and recovery platform for Indian consumers."
    ),
    version="0.1.0",
)

@app.get("/")
async def root():
    return {
        "application": "PayPause",
        "tagline": "Think Before Money Moves.",
        "status": "running",
        "version": "0.1.0",
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "paypause-api",
    }
