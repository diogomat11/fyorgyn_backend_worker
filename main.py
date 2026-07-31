import os
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import jobs, workers, internal, crm

app = FastAPI(
    title="FyorGyn Worker API", 
    version="1.0.0",
    description="Bridge API para gerenciamento de jobs do Worker"
)

# CORS configurations
cors_origins_raw = os.getenv("CORS_ORIGINS", "*")
origins = [origin.strip() for origin in cors_origins_raw.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {
        "status": "ok", 
        "service": "FyorGyn Worker API",
        "timestamp": datetime.utcnow().isoformat() if "datetime" in globals() else None
    }

# Include routers
app.include_router(jobs.router, tags=["Jobs"])
app.include_router(workers.router, tags=["Workers"])
app.include_router(internal.router, tags=["Internal"])
app.include_router(crm.router, tags=["CRM"])

