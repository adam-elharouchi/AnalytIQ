"""
Supabase Storage Client for AnalytIQ
Handles PDF file uploads, downloads, and migrations to Supabase Storage
"""

import config

# Supabase configuration
SUPABASE_URL = config.SUPABASE_URL
SUPABASE_KEY = config.SUPABASE_KEY
SUPABASE_BUCKET = config.SUPABASE_BUCKET

# Initialize Supabase client
try:
    from supabase import create_client, Client

    if SUPABASE_URL and SUPABASE_KEY:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"✅ Supabase client initialized (bucket: {SUPABASE_BUCKET})")
    else:
        supabase = None
        print("⚠️  Supabase credentials not configured")
except ImportError:
    supabase = None
    print("⚠️  Supabase library not installed")


def upload_pdf(file_bytes, filename):
    """
    Upload PDF to Supabase Storage

    Args:
        file_bytes: PDF file as bytes
        filename: Filename to store (should be unique)

    Returns:
        str: Public URL of uploaded file, or None if failed
    """
    if not supabase:
        raise ValueError("Supabase client not initialized")

    try:
        # Upload file to storage
        response = supabase.storage.from_(SUPABASE_BUCKET).upload(
            path=filename, file=file_bytes, file_options={"content-type": "application/pdf"}
        )

        # Get public URL
        public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(filename)

        return public_url

    except Exception as e:
        print(f"Error uploading PDF: {e}")
        return None


def get_pdf_url(filename, expires_in=3600):
    """
    Get signed URL for PDF (valid for specified duration)

    Args:
        filename: Filename in storage
        expires_in: URL expiration time in seconds (default: 1 hour)

    Returns:
        str: Signed URL, or None if failed
    """
    if not supabase:
        raise ValueError("Supabase client not initialized")

    try:
        # Create signed URL
        signed_url = supabase.storage.from_(SUPABASE_BUCKET).create_signed_url(
            path=filename, expires_in=expires_in
        )

        return signed_url["signedURL"] if signed_url else None

    except Exception as e:
        print(f"Error getting PDF URL: {e}")
        return None


def delete_pdf(filename):
    """
    Delete PDF from Supabase Storage

    Args:
        filename: Filename to delete

    Returns:
        bool: True if successful, False otherwise
    """
    if not supabase:
        raise ValueError("Supabase client not initialized")

    try:
        response = supabase.storage.from_(SUPABASE_BUCKET).remove([filename])
        return True

    except Exception as e:
        print(f"Error deleting PDF: {e}")
        return False


def get_presigned_upload_url(storage_path):
    """
    Create a presigned upload URL for direct browser-to-Supabase upload.

    Args:
        storage_path: Unique path in the bucket (e.g. "chapters/abc123_file.pdf")

    Returns:
        dict with {"signedURL": str, "token": str, "path": str}, or None on failure.
    """
    if not supabase:
        raise ValueError("Supabase client not initialized")
    try:
        response = supabase.storage.from_(SUPABASE_BUCKET).create_signed_upload_url(storage_path)
        return response
    except Exception as e:
        print(f"Error creating presigned upload URL: {e}")
        return None


def migrate_pdf_from_db(chapter_id, pdf_data, pdf_filename):
    """
    Migrate a single PDF from database to Supabase Storage

    Args:
        chapter_id: Chapter ID
        pdf_data: PDF bytes from database
        pdf_filename: Original filename

    Returns:
        dict: {'success': bool, 'url': str or None, 'error': str or None}
    """
    if not supabase:
        return {"success": False, "url": None, "error": "Supabase client not initialized"}

    try:
        # Generate unique filename
        import uuid

        unique_filename = f"{chapter_id}_{uuid.uuid4().hex[:8]}_{pdf_filename}"

        # Upload to Supabase
        public_url = upload_pdf(bytes(pdf_data), unique_filename)

        if not public_url:
            return {"success": False, "url": None, "error": "Upload failed"}

        return {"success": True, "url": public_url, "error": None, "filename": unique_filename}

    except Exception as e:
        return {"success": False, "url": None, "error": str(e)}


def storage_health_check():
    """
    Check if Supabase Storage is accessible

    Returns:
        dict: {'healthy': bool, 'message': str}
    """
    if not supabase:
        return {"healthy": False, "message": "Supabase client not initialized"}

    try:
        # Try to list files (no limit parameter in newer API)
        response = supabase.storage.from_(SUPABASE_BUCKET).list()

        return {"healthy": True, "message": "Supabase Storage accessible"}

    except Exception as e:
        return {"healthy": False, "message": f"Supabase Storage error: {str(e)}"}
