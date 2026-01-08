"""
RutasFast - Authentication utilities
JWT access + refresh tokens with rotation and cookie support
"""
import os
import secrets
import hashlib
import hmac
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from jose import jwt, JWTError
from passlib.context import CryptContext
import bcrypt

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Cookie configuration
COOKIE_NAME = "refresh_token"
COOKIE_PATH = "/api/auth"
COOKIE_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # in seconds

# Detect production environment
IS_PRODUCTION = (
    os.environ.get("ENVIRONMENT") == "production" or
    os.environ.get("VERCEL_ENV") == "production" or
    os.environ.get("RAILWAY_ENVIRONMENT") == "production" or
    bool(os.environ.get("RENDER"))  # Render.com
)

# Cookie secure flag - must be True in production with HTTPS
COOKIE_SECURE = IS_PRODUCTION or os.environ.get("COOKIE_SECURE", "false").lower() == "true"
# SameSite - Lax is safer for cross-site in subdomains; Strict for same-site
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "lax")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str, email: str) -> str:
    """Create JWT access token"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Create JWT refresh token"""
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": secrets.token_hex(16)  # Unique token ID for rotation
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_reset_token() -> Tuple[str, str]:
    """Generate a secure password reset token and its hash"""
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash


def hash_reset_token(token: str) -> str:
    """Hash a reset token for lookup"""
    return hashlib.sha256(token.encode()).hexdigest()


def verify_reset_token_hash(token: str, stored_hash: str) -> bool:
    """Compare token hash in constant time to prevent timing attacks"""
    computed_hash = hashlib.sha256(token.encode()).hexdigest()
    return hmac.compare_digest(computed_hash, stored_hash)


# Admin authentication
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH")
# Detect production: Emergent, Vercel, or explicit ENVIRONMENT
IS_PRODUCTION = (
    os.environ.get("ENVIRONMENT") == "production" or
    os.environ.get("VERCEL_ENV") == "production" or
    os.environ.get("RAILWAY_ENVIRONMENT") == "production" or
    bool(os.environ.get("RENDER"))  # Render.com
)


def verify_admin_password(password: str) -> bool:
    """Verify admin password against stored hash"""
    # In production, REQUIRE real credentials
    if IS_PRODUCTION:
        if not ADMIN_PASSWORD_HASH:
            # No hash configured in production = fail
            return False
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                ADMIN_PASSWORD_HASH.encode('utf-8')
            )
        except Exception:
            return False
    
    # Development fallback
    if not ADMIN_PASSWORD_HASH:
        return password == "admin123"
    
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            ADMIN_PASSWORD_HASH.encode('utf-8')
        )
    except Exception:
        return False


def create_admin_token() -> str:
    """Create JWT token for admin"""
    expire = datetime.now(timezone.utc) + timedelta(hours=8)
    payload = {
        "sub": "admin",
        "type": "admin",
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
