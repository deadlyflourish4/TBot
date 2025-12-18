import os
from fastapi import Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()
STATIC_TOKEN = os.getenv("STATIC_TOKEN")

async def jwt_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing Authorization header"},
            )

        token = auth_header.split(" ")[1]
        if token != STATIC_TOKEN:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"},
            )

    return await call_next(request)
