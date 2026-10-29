from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router
from app.database.database import engine, Base
from app.email.email_service import EmailService
from app.worker import celery_app
from app.metrics import metrics_middleware
import os
from prometheus_client import make_asgi_app
from fastapi.responses import PlainTextResponse, JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from datetime import datetime, timezone
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")
except Exception as e:
    print(f"Error creating database tables: {str(e)}")

# Create FastAPI app
app = FastAPI(
    title="Reservation System API",
    description="API for managing reservations, guests, and units",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agregar middleware de métricas
app.middleware("http")(metrics_middleware)

# Agregar endpoint de métricas
@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Include API routes
app.include_router(router, prefix="/api/v1")

# Initialize email service
email_service = EmailService()

@app.get("/")
async def root():
    return {"message": "Welcome to the Reservation System API"}

# ----------------- Standardized Error Handlers -----------------

# 1. Handles Pydantic Input Validation Errors (HTTP 422)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Extract the first human-readable validation error message
    first_error = exc.errors()[0] if exc.errors() else {}
    error_msg = first_error.get("msg", "Invalid input data")
    field = ".".join(str(loc) for loc in first_error.get("loc", []))
    
    return JSONResponse(
        status_code=422,
        content={
            "success": false,
            "status_code": 422,
            "error_type": "VALIDATION_ERROR",
            "message": f"{field}: {error_msg}" if field else error_msg,
            "path": str(request.url.path),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

# 2. Handles Standard HTTP Exceptions (400, 404, 409, etc.)
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": false,
            "status_code": exc.status_code,
            "error_type": "HTTP_ERROR",
            "message": exc.detail,
            "path": str(request.url.path),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

# 3. Global Fallback for Unexpected Crashes (HTTP 500)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": false,
            "status_code": 500,
            "error_type": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
            "path": str(request.url.path),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )