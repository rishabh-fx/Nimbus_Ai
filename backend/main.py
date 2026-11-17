'''FastAPI() creates backend application.
    Starts the FastAPI application


CORSMiddleware allows frontend to communicate with your backend.



app.include_router(router) connects the endpoints defined in api.py.



/ provides basic application information.'''

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import router
from backend.config import ALLOWED_ORIGINS

# Create FastAPI application
app = FastAPI(
    title="Nimbus AI",
    description="Enterprise RAG Value Intelligence Assistant",
    version="1.0.0"
)

# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Connect API routes
app.include_router(router)


@app.get("/")
def root():
    return {
        "application": "Nimbus AI",
        "message": "Enterprise RAG Value Intelligence Assistant",
        "docs": "/docs",
        "health": "/health"
    }
