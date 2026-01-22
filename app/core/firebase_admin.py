"""
Firebase Admin SDK initialization for token verification.

This module initializes Firebase Admin SDK using the same credentials
as Firestore (Google Cloud service account).
"""

import firebase_admin
from firebase_admin import credentials, auth
import os
import logging

logger = logging.getLogger(__name__)

# Global flag to track initialization
_initialized = False


def init_firebase_admin():
    """
    Initialize Firebase Admin SDK if not already initialized.
    
    Uses the same Google Cloud credentials as Firestore.
    """
    global _initialized
    
    if _initialized:
        return auth
    
    if not firebase_admin._apps:
        try:
            # Use Application Default Credentials (same as Firestore)
            # This will use:
            # 1. GOOGLE_APPLICATION_CREDENTIALS env var (path to JSON)
            # 2. Default credentials from gcloud auth
            # 3. Service account from metadata server (GCP)
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
            raise
    
    _initialized = True
    return auth


def get_firebase_auth():
    """
    Get Firebase Auth instance.
    
    Returns:
        Firebase Auth instance for token verification
    """
    init_firebase_admin()
    return auth
