import os
import sys
import json

# Add parent directory to path to allow imports when running directly
# This must be done before importing app modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file if it exists
load_dotenv()


# Handle Google credentials - MUST be set up before importing anything that uses Firestore
def setup_google_credentials():
    """
    Set up Google Cloud credentials for Firestore.
    Handles multiple scenarios:
    1. Local JSON file (for local development)
    2. Environment variable with JSON string (for deployment platforms like Render)
    3. Default credentials (if already set via gcloud auth)
    """
    try:
        # First check for JSON file (local development)
        if os.path.exists("api-key.json"):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "api-key.json"
            logger.info("Using local credentials file: api-key.json")
            return

        # If no file, try environment variable (Render or .env file)
        creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        if creds_json:
            # For local development, the JSON might be a string representation
            if isinstance(creds_json, str) and creds_json.startswith("{"):
                creds_json = json.loads(creds_json)

            # Create a temporary file to store credentials
            creds_path = (
                "/tmp/google-credentials.json"
                if os.getenv("RENDER")
                else "temp-credentials.json"
            )
            with open(creds_path, "w") as f:
                if isinstance(creds_json, dict):
                    json.dump(creds_json, f)
                else:
                    f.write(creds_json)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
            logger.info("Successfully set up Google credentials from environment")
        else:
            logger.info(
                "No explicit credentials found, using default credentials (gcloud auth or metadata server)"
            )
    except Exception as e:
        logger.error(f"Error setting up Google credentials: {e}")


# Set up credentials before anything else
setup_google_credentials()

# Now import modules that use Firestore (after credentials are set)
from app.core.database import init_db
from app.api.v1 import (
    assessments,
    results,
    auth,
    resources,
    interview_context,
    interview,
    analytics,
    users,
    feature_requests,
)

# Create FastAPI app
app = FastAPI(
    title="Question Bank API",
    description="API for generating and managing assessments with AI agents",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:3000",
        "http://localhost:4173",
        "https://interview-hub1.netlify.app",
        "https://id-preview--d72cdb61-6a23-4e77-87a8-02153d82ab6a.lovable.app"
    ],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("Application started successfully")
    logger.info("AI Agents available:")
    logger.info("  - Generator Agent: /v1/assessments/generate")
    logger.info("  - Feedback Agent: /v1/assessments/submit")
    logger.info("  - Interview Context Agent: /v1/interview-context/generate")
    logger.info(
        "  - Primary Question Generator: /v1/interview/generate-primary-question"
    )


# Include routers
app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
app.include_router(assessments.router, prefix="/v1/assessments", tags=["assessments"])
app.include_router(results.router, prefix="/v1/results", tags=["results"])
app.include_router(resources.router, prefix="/v1/resources", tags=["resources"])
app.include_router(
    interview_context.router, prefix="/v1/interview-context", tags=["interview-context"]
)
app.include_router(interview.router, prefix="/v1/interview", tags=["interview"])
app.include_router(analytics.router, prefix="/v1/analytics", tags=["analytics"])
app.include_router(users.router, prefix="/v1/users", tags=["users"])
app.include_router(feature_requests.router, prefix="/v1/feature-requests", tags=["feature-requests"])

@app.get("/")
async def root():
    return {
        "message": "Question Bank API",
        "version": "1.0.0",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json",
        },
        "endpoints": {
            "signup": "POST /v1/auth/signup",
            "login": "POST /v1/auth/login",
            "migrate_guest": "POST /v1/auth/migrate-guest",
            "generate_assessment": "POST /v1/assessments/generate",
            "submit_assessment": "POST /v1/assessments/submit",
            "get_results": "GET /v1/assessments/{id}/results",
            "get_result": "GET /v1/results/{id}",
            "generate_interview_context": "POST /v1/interview-context/generate",
            "generate_primary_question": "POST /v1/interview/generate-primary-question",
            "create_feature_request": "POST /v1/feature-requests",
            "list_feature_requests": "GET /v1/feature-requests",
            "vote_feature_request": "POST /v1/feature-requests/{id}/vote",
            "health": "GET /health",
        },
    }


@app.get("/health")
async def health_check():
    logger.info("Health check endpoint called")
    return {"status": "healthy"}


# Add request logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response


if __name__ == "__main__":
    # Use the PORT environment variable, defaulting to 8080
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
