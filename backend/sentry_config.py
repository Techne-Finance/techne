"""
Sentry Error Monitoring Configuration
Production-grade error tracking for Techne Finance backend
"""
import os
import logging
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


def filter_sensitive_data(event, hint):
    """Remove sensitive financial data from Sentry events."""
    sensitive_keys = ['private_key', 'signature', 'password', 'api_key', 'secret', 'mnemonic', 'seed']
    
    # Filter request body
    if 'request' in event and 'data' in event['request']:
        data = event['request']['data']
        if isinstance(data, dict):
            for key in sensitive_keys:
                if key in data:
                    data[key] = '[FILTERED]'
    
    # Filter exception values that might contain keys
    if 'exception' in event and 'values' in event['exception']:
        for exc in event['exception']['values']:
            if 'value' in exc:
                for key in sensitive_keys:
                    if key in exc['value'].lower():
                        exc['value'] = '[FILTERED - sensitive data]'
    
    return event


def init_sentry():
    """Initialize Sentry with appropriate configuration."""
    dsn = os.getenv("SENTRY_DSN")
    
    if not dsn:
        print("[Sentry] No SENTRY_DSN found - error tracking disabled")
        return False
    
    environment = os.getenv("ENVIRONMENT", "development")
    release = os.getenv("COMMIT_SHA", "local")
    
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        
        # Enable performance monitoring
        traces_sample_rate=0.2,  # 20% of transactions
        profiles_sample_rate=0.1,  # 10% profiling
        
        # FastAPI integrations
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.WARNING
            ),
        ],
        
        # Filter sensitive data
        before_send=filter_sensitive_data,
        
        # Privacy settings
        send_default_pii=False,  # GDPR compliant
        
        # Release tracking
        release=f"techne-backend@{release}",
        
        # Ignore expected errors
        ignore_errors=[
            ConnectionRefusedError,
            TimeoutError,
        ],
    )
    
    print(f"[Sentry] ✓ Initialized for {environment} (release: {release[:8]})")
    return True


def capture_agent_context(user_address: str, agent_id: str = None):
    """Add user context to Sentry for agent operations."""
    if not user_address:
        return
        
    sentry_sdk.set_user({
        "id": user_address[:10] + "...",  # Truncated for privacy
    })
    sentry_sdk.set_context("agent", {
        "agent_id": agent_id,
        "wallet": user_address[:10] + "..." if user_address else None,
    })


def capture_transaction_breadcrumb(action: str, details: dict = None):
    """Add breadcrumb for financial transactions."""
    sentry_sdk.add_breadcrumb(
        category="transaction",
        message=action,
        level="info",
        data=details or {}
    )


def capture_blockchain_breadcrumb(action: str, chain: str = "base", details: dict = None):
    """Add breadcrumb for blockchain interactions."""
    sentry_sdk.add_breadcrumb(
        category="blockchain",
        message=action,
        level="info",
        data={"chain": chain, **(details or {})}
    )


def set_request_context(endpoint: str, method: str = "GET"):
    """Set context for the current request."""
    sentry_sdk.set_tag("endpoint", endpoint)
    sentry_sdk.set_tag("method", method)
