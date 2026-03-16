"""
Sentry Integration for Production Error Monitoring
"""
import os
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.celery import CeleryIntegration


def init_sentry(app):
    """
    Initialize Sentry error tracking for production monitoring
    
    Features:
    - Automatic error capture and reporting
    - Performance monitoring (transactions)
    - Release tracking for deployment correlation
    - Environment tagging (production/staging)
    """
    sentry_dsn = os.getenv('SENTRY_DSN')
    environment = os.getenv('FLASK_ENV', 'production')
    
    if not sentry_dsn:
        app.logger.warning("⚠️  Sentry DSN not configured. Error monitoring disabled.")
        return
    
    # Get app version from environment or git
    release_version = os.getenv('RENDER_GIT_COMMIT', 'unknown')[:7]
    
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            FlaskIntegration(),
            RedisIntegration(),
            CeleryIntegration(),
        ],
        
        # Performance Monitoring
        traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
        
        # Error Sampling
        sample_rate=1.0,  # Capture 100% of errors
        
        # Environment Configuration
        environment=environment,
        release=f"analytiq@{release_version}",
        
        # Additional Context
        send_default_pii=False,  # Don't send personally identifiable information
        attach_stacktrace=True,
        
        # Before Send Hook (filter sensitive data)
        before_send=filter_sensitive_data,
    )
    
    app.logger.info(f"✅ Sentry initialized for {environment} environment")


def filter_sensitive_data(event, hint):
    """
    Filter sensitive data before sending to Sentry
    
    Removes:
    - API keys
    - Passwords
    - Session tokens
    - Email addresses (in some contexts)
    """
    # Remove sensitive headers
    if 'request' in event:
        headers = event['request'].get('headers', {})
        sensitive_headers = ['Authorization', 'Cookie', 'X-API-Key']
        for header in sensitive_headers:
            if header in headers:
                headers[header] = '[Filtered]'
    
    # Remove sensitive POST data
    if 'request' in event and 'data' in event['request']:
        data = event['request']['data']
        if isinstance(data, dict):
            sensitive_fields = ['password', 'api_key', 'secret', 'token']
            for field in sensitive_fields:
                if field in data:
                    data[field] = '[Filtered]'
    
    return event


def capture_exception_with_context(exception, context=None):
    """
    Manually capture an exception with additional context
    
    Usage:
        try:
            risky_operation()
        except Exception as e:
            capture_exception_with_context(e, {
                'user_id': user_id,
                'operation': 'pdf_upload'
            })
    """
    if context:
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_context(key, value)
            sentry_sdk.capture_exception(exception)
    else:
        sentry_sdk.capture_exception(exception)


def capture_message(message, level='info', context=None):
    """
    Capture a custom message in Sentry
    
    Levels: 'debug', 'info', 'warning', 'error', 'fatal'
    """
    if context:
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_context(key, value)
            sentry_sdk.capture_message(message, level=level)
    else:
        sentry_sdk.capture_message(message, level=level)
