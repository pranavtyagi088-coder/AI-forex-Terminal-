import os
import hmac
import hashlib
import json
import base64
import time
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

security = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    key = hashlib.pbkdf2_hmac(
        'sha256', 
        password.encode('utf-8'), 
        bytes.fromhex(salt), 
        100000
    ).hex()
    return f"{salt}${key}"

def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, stored_hash = hashed.split('$')
        computed_hash = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            bytes.fromhex(salt), 
            100000
        ).hex()
        return hmac.compare_digest(stored_hash, computed_hash)
    except Exception:
        return False

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def _b64url_decode(data_str: str) -> bytes:
    pad = len(data_str) % 4
    if pad:
        data_str += '=' * (4 - pad)
    return base64.urlsafe_b64decode(data_str.encode('utf-8'))

def create_jwt_token(payload: Dict[str, Any], expires_in_seconds: int = 86400) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload_copy = dict(payload)
    payload_copy["exp"] = int(time.time()) + expires_in_seconds
    
    header_b64 = _b64url_encode(json.dumps(header).encode('utf-8'))
    payload_b64 = _b64url_encode(json.dumps(payload_copy).encode('utf-8'))
    signing_input = f"{header_b64}.{payload_b64}"
    
    signature = hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        signing_input.encode('utf-8'),
        hashlib.sha256
    ).digest()
    sig_b64 = _b64url_encode(signature)
    return f"{signing_input}.{sig_b64}"

def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode('utf-8'),
            signing_input.encode('utf-8'),
            hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_b64url_encode(expected_sig), sig_b64):
            return None
        payload = json.loads(_b64url_decode(payload_b64).decode('utf-8'))
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer Token"
        )
    
    token = credentials.credentials
    if token == settings.API_AUTH_TOKEN:
        return User(id=0, username="MasterAdmin", role="admin", is_active=True)

    payload = decode_jwt_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user_id = payload.get("sub")
    res = await db.execute(select(User).where(User.id == int(user_id)))
    user = res.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")
    return user

async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user

async def require_api_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    token = credentials.credentials
    if token == settings.API_AUTH_TOKEN:
        return True
    payload = decode_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return True

# Alias for backward compatibility with upload / analysis / market routes
verify_api_token = require_api_token
