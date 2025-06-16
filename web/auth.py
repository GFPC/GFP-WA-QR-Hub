from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
security = HTTPBearer()


async def verify_secret_key(request: Request, credentials: HTTPAuthorizationCredentials):
    """Verify the secret key from the request header."""
    if credentials.credentials != settings.SECRET_KEY:
        logger.warning(f"Invalid secret key attempt from {request.client.host}")
        raise HTTPException(
            status_code=403,
            detail="Invalid secret key"
        )
    return True


class SecretKeyAuth:
    async def __call__(self, request: Request):
        try:
            credentials = await security(request)
            await verify_secret_key(request, credentials)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials"
            ) 