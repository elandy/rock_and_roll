from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings


api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)


def require_api_key(
    api_key: str | None = Security(api_key_header),
) -> None:
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "unauthorized",
                "message": "Invalid or missing API key",
            },
        )