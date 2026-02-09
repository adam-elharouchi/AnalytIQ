#!/usr/bin/env python3
"""
Deployment Verification Script
Run this on Render to verify all environment variables and integrations are working.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_env_var(name, required=True, secret=False):
    """Check if environment variable is set."""
    value = os.getenv(name)
    if value:
        if secret:
            display_value = f"{value[:10]}..." if len(value) > 10 else "***"
        else:
            display_value = value
        print(f"  ✅ {name}: {display_value}")
        return True
    else:
        status = "❌" if required else "⚠️"
        print(f"  {status} {name}: NOT SET")
        return not required

def check_import(module_name, description):
    """Check if a module can be imported."""
    try:
        __import__(module_name)
        print(f"  ✅ {description}")
        return True
    except ImportError as e:
        print(f"  ❌ {description}: {e}")
        return False

def check_database():
    """Check database connection."""
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("  ❌ DATABASE_URL not set")
            return False
        
        # Parse URL
        result = urlparse(db_url)
        
        # Try to connect
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        conn.close()
        print("  ✅ Database connection successful")
        return True
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        return False

def check_redis():
    """Check Redis connection."""
    try:
        import redis
        
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            print("  ❌ REDIS_URL not set")
            return False
        
        r = redis.from_url(redis_url)
        r.ping()
        print("  ✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"  ❌ Redis connection failed: {e}")
        return False

def check_supabase():
    """Check Supabase connection."""
    try:
        from supabase import create_client
        
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            print("  ❌ SUPABASE_URL or SUPABASE_KEY not set")
            return False
        
        client = create_client(url, key)
        # Try to list buckets
        client.storage.list_buckets()
        print("  ✅ Supabase connection successful")
        return True
    except Exception as e:
        print(f"  ❌ Supabase connection failed: {e}")
        return False

def check_jwt():
    """Check JWT implementation."""
    try:
        import jwt
        from app import create_jwt_token, decode_jwt_token
        
        # Create a test token
        token = create_jwt_token("test_user", role="student", name="Test", email="test@test.com")
        
        # Decode it
        payload = decode_jwt_token(token)
        
        if payload["user_id"] == "test_user" and payload["role"] == "student":
            print("  ✅ JWT implementation working")
            return True
        else:
            print("  ❌ JWT payload incorrect")
            return False
    except Exception as e:
        print(f"  ❌ JWT check failed: {e}")
        return False

def main():
    print("=" * 80)
    print("DEPLOYMENT VERIFICATION")
    print("=" * 80)
    
    all_checks_passed = True
    
    # Check critical environment variables
    print("\n1. Critical Environment Variables:")
    all_checks_passed &= check_env_var("FLASK_ENV", required=True)
    all_checks_passed &= check_env_var("SECRET_KEY", required=True, secret=True)
    all_checks_passed &= check_env_var("DATABASE_URL", required=True, secret=True)
    all_checks_passed &= check_env_var("REDIS_URL", required=True, secret=True)
    
    # Check external service credentials
    print("\n2. External Service Credentials:")
    all_checks_passed &= check_env_var("GEMINI_API_KEY", required=True, secret=True)
    all_checks_passed &= check_env_var("SUPABASE_URL", required=True)
    all_checks_passed &= check_env_var("SUPABASE_KEY", required=True, secret=True)
    all_checks_passed &= check_env_var("SENTRY_DSN", required=True, secret=True)
    
    # Check email configuration
    print("\n3. Email Configuration:")
    all_checks_passed &= check_env_var("MAIL_SERVER", required=True)
    all_checks_passed &= check_env_var("MAIL_PORT", required=True)
    all_checks_passed &= check_env_var("MAIL_USERNAME", required=True)
    all_checks_passed &= check_env_var("MAIL_PASSWORD", required=True, secret=True)
    all_checks_passed &= check_env_var("MAIL_DEFAULT_SENDER", required=True)
    
    # Check CORS configuration
    print("\n4. CORS Configuration:")
    all_checks_passed &= check_env_var("CORS_ORIGINS", required=True)
    cors_origins = os.getenv("CORS_ORIGINS", "")
    if "*" in cors_origins and os.getenv("FLASK_ENV") == "production":
        print("  ⚠️  WARNING: CORS allows all origins (*) in production!")
        all_checks_passed = False
    
    # Check feature flags
    print("\n5. Feature Flags:")
    check_env_var("FEATURE_CACHING", required=False)
    check_env_var("FEATURE_ASYNC_TASKS", required=False)
    check_env_var("FEATURE_CSRF", required=False)
    check_env_var("FEATURE_EMAIL", required=False)
    
    # Check optional variables
    print("\n6. Optional Variables:")
    check_env_var("SUPABASE_BUCKET", required=False)
    check_env_var("JWT_SECRET_KEY", required=False)
    
    # Check Python dependencies
    print("\n7. Python Dependencies:")
    all_checks_passed &= check_import("flask", "Flask")
    all_checks_passed &= check_import("psycopg2", "psycopg2 (PostgreSQL)")
    all_checks_passed &= check_import("redis", "redis")
    all_checks_passed &= check_import("celery", "Celery")
    all_checks_passed &= check_import("supabase", "Supabase")
    all_checks_passed &= check_import("jwt", "PyJWT")
    all_checks_passed &= check_import("sentry_sdk", "Sentry SDK")
    all_checks_passed &= check_import("flask_limiter", "Flask-Limiter")
    all_checks_passed &= check_import("flask_wtf", "Flask-WTF")
    
    # Check connections
    print("\n8. Service Connections:")
    all_checks_passed &= check_database()
    all_checks_passed &= check_redis()
    all_checks_passed &= check_supabase()
    
    # Check JWT implementation
    print("\n9. JWT Authentication:")
    all_checks_passed &= check_jwt()
    
    # Check config
    print("\n10. Configuration:")
    try:
        import config
        print(f"  ✅ Environment: {config.ENV}")
        print(f"  ✅ Debug mode: {config.DEBUG}")
        print(f"  ✅ CSRF enabled: {config.FEATURE_CSRF_PROTECTION}")
        print(f"  ✅ Caching enabled: {config.FEATURE_CACHING}")
        print(f"  ✅ Async tasks enabled: {config.FEATURE_ASYNC_TASKS}")
        
        # Security checks
        if config.DEBUG and config.ENV == "production":
            print("  ❌ WARNING: Debug mode is ON in production!")
            all_checks_passed = False
        
        if config.SECRET_KEY == "dev-secret-key-change-in-production":
            print("  ❌ WARNING: Using default SECRET_KEY!")
            all_checks_passed = False
            
    except Exception as e:
        print(f"  ❌ Config check failed: {e}")
        all_checks_passed = False
    
    # Final result
    print("\n" + "=" * 80)
    if all_checks_passed:
        print("✅ ALL CHECKS PASSED - Deployment is ready!")
    else:
        print("❌ SOME CHECKS FAILED - Please review the errors above")
        sys.exit(1)
    print("=" * 80)

if __name__ == "__main__":
    main()
