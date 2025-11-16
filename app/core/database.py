from google.cloud import firestore
from typing import Generator, Optional

# Lazy initialization - only create client when needed
# This allows credentials to be set up before Firestore tries to initialize
_db_client: Optional[firestore.Client] = None


def get_firestore_client() -> firestore.Client:
    """
    Get or create Firestore client (lazy initialization).
    Automatically uses credentials from:
    1. GOOGLE_APPLICATION_CREDENTIALS environment variable (path to service account JSON)
    2. Default credentials from gcloud auth application-default login
    3. Service account from metadata server (if running on GCP)
    """
    global _db_client
    if _db_client is None:
        _db_client = firestore.Client()
    return _db_client


def get_db() -> Generator[firestore.Client, None, None]:
    """
    Dependency function to get Firestore client.
    """
    yield get_firestore_client()


def init_db():
    """
    Initialize Firestore database.
    Firestore doesn't require explicit table creation - collections are created on first write.
    """
    # Firestore collections are created automatically on first write
    # No initialization needed
    pass
