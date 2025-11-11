import os
from fastapi import Security, Depends, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

API_KEY_NAME = 'X-API-Key'
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def get_api_key(api_key: str = Security(api_key_header)):
    """
    Validate the API key from the X-API-Key header against environment variable.

    Args:
        api_key: The API key from the request header

    Returns:
        The validated API key

    Raises:
        HTTPException: If the API key is invalid
    """
    # In a production system, fetch from a secure secret manager or database
    expected_api_key = os.getenv('SUPER_SECRET_API_KEY')

    if not expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='API key not configured on server'
        )

    if api_key == expected_api_key:
        return api_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Invalid API Key',
        headers={'WWW-Authenticate': 'API Key'}
    )