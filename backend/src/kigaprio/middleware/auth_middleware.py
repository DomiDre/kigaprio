from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class TokenRefreshMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Process the request normally
        response = await call_next(request)

        # Check if the request context has a new token
        # (This is set by verify_token when a refresh happens)
        if hasattr(request.state, "new_token"):
            response.headers["X-New-Token"] = request.state.new_token

        return response
