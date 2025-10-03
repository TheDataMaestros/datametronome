"""
Middleware for DataMetronome Podium.

Provides request tracking, metrics collection, and logging.
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect Prometheus metrics for HTTP requests.
    
    Tracks:
    - Request count by method, endpoint, and status
    - Request duration
    - Requests in progress
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        from .metrics import record_http_request, http_requests_in_progress
        
        # Get endpoint path (without query parameters)
        endpoint = request.url.path
        method = request.method
        
        # Track in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()
        
        # Track request timing
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code
            
            return response
            
        except Exception as e:
            # Record error status
            status_code = 500
            logger.error(f"Request failed: {method} {endpoint} - {e}")
            raise
            
        finally:
            # Calculate duration
            duration = time.time() - start_time
            
            # Record metrics
            record_http_request(method, endpoint, status_code, duration)
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()
            
            # Log request
            logger.info(
                f"{method} {endpoint} {status_code} {duration:.3f}s",
                extra={
                    "method": method,
                    "endpoint": endpoint,
                    "status_code": status_code,
                    "duration_seconds": duration
                }
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for detailed request logging.
    
    Logs all requests with:
    - Request details (method, path, headers)
    - Response status
    - Request duration
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process and log request."""
        start_time = time.time()
        
        # Log request
        logger.debug(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        log_level = logging.INFO if response.status_code < 400 else logging.WARNING
        logger.log(
            log_level,
            f"Request completed: {request.method} {request.url.path} "
            f"-> {response.status_code} in {duration:.3f}s",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_seconds": duration,
            }
        )
        
        return response

