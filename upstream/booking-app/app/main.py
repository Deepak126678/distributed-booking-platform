from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse, JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from datetime import datetime, timezone
import uuid
import time
import logging

from app.api.endpoints import router
from app.database.database import engine, Base
from app.email.email_service import EmailService
from app.worker import celery_app
from app.metrics import metrics_middleware

# ----------------- Structured Logging -----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("booking-api")

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created successfully")
except Exception as e:
    logger.error(f"Error creating database tables: {str(e)}")

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

# ----------------- Middlewares -----------------

# 1. Prometheus Metrics Middleware
app.middleware("http")(metrics_middleware)

# 2. X-Request-ID & Request Tracing Middleware
@app.middleware("http")
async def request_id_and_logging_middleware(request: Request, call_next):
    start_time = time.time()
    
    # Grab X-Request-ID from incoming request (from Nginx), or generate a fresh UUID
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    
    logger.info(f"[{request_id}] --> {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(f"[{request_id}] <X- UNHANDLED ERROR in {duration_ms}ms: {exc}")
        raise exc
        
    duration_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(f"[{request_id}] <-- {request.method} {request.url.path} {response.status_code} ({duration_ms}ms)")
    
    # Inject X-Request-ID into outgoing response headers
    response.headers["X-Request-ID"] = request_id
    return response

# ----------------- Core Routes -----------------

@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

app.include_router(router, prefix="/api/v1")

email_service = EmailService()

@app.get("/")
async def root():
    return {"message": "Welcome to the Reservation System API"}

# ----------------- Standardized Error Handlers -----------------

# 1. Handles Pydantic Input Validation Errors (HTTP 422)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
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
            "request_id": getattr(request.state, "request_id", None),
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
            "request_id": getattr(request.state, "request_id", None),
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
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )