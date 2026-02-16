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
# SECURITY: JWT_SECRET is REQUIRED in production, fail-closed
_jwt_secret_raw = os.environ.get("JWT_SECRET")

# Detect production environment (defined early for JWT validation)
IS_PRODUCTION = (
    os.environ.get("ENVIRONMENT") == "production" or  # Explicit (preferred)
    os.environ.get("VERCEL_ENV") == "production" or   # Vercel
    os.environ.get("RAILWAY_ENVIRONMENT") == "production" or  # Railway
    (bool(os.environ.get("RENDER")) and os.environ.get("ENVIRONMENT") != "development")  # Render (with dev override)
)

# Fail-closed: Production MUST have JWT_SECRET configured
if IS_PRODUCTION and not _jwt_secret_raw:
    raise RuntimeError(
        "SECURITY ERROR: JWT_SECRET environment variable is REQUIRED in production. "
        "Set a strong, unique secret (min 32 chars) before deploying."
    )

# Development fallback (only when NOT in production)
JWT_SECRET = _jwt_secret_raw or "dev-secret-change-in-production"

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Cookie configuration
COOKIE_NAME = "refresh_token"
COOKIE_PATH = "/api/auth"
COOKIE_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # in seconds

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


def create_refresh_token(user_id: str, token_version: int = 0) -> str:
    """Create JWT refresh token with token_version for revocation"""
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": secrets.token_hex(16),  # Unique token ID for rotation
        "v": token_version  # Token version for logout/revocation
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
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")

# Handle ADMIN_PASSWORD_HASH - support both plain and Base64 encoded
_raw_admin_hash = os.environ.get("ADMIN_PASSWORD_HASH", "")

def _decode_admin_hash(raw_value: str) -> str:
    """
    Decode admin password hash from env.
    Supports:
    - Plain bcrypt hash (starts with $2b$, $2a$, or $2y$)
    - Base64 encoded hash (for deployment environments that strip $ chars)
    """
    if not raw_value:
        return ""
    
    # Check if it looks like a valid bcrypt hash already
    if raw_value.startswith(("$2b$", "$2a$", "$2y$")):
        return raw_value
    
    # Try Base64 decode
    try:
        import base64
        decoded = base64.b64decode(raw_value).decode('utf-8')
        if decoded.startswith(("$2b$", "$2a$", "$2y$")):
            return decoded
    except Exception:
        pass
    
    # Return as-is (might be corrupted, will fail verification)
    return raw_value

ADMIN_PASSWORD_HASH = _decode_admin_hash(_raw_admin_hash)

# Default dev credentials (only used in non-production when env vars not set)
DEFAULT_DEV_USERNAME = "admin"
DEFAULT_DEV_PASSWORD = "admin123"


def is_admin_env_configured() -> bool:
    """Check if admin credentials are explicitly configured via env vars"""
    return bool(ADMIN_USERNAME and ADMIN_PASSWORD_HASH)


def is_admin_configured() -> bool:
    """Check if admin login is available (either env or dev defaults)"""
    if IS_PRODUCTION:
        return is_admin_env_configured()
    return True  # Dev allows defaults


def get_admin_username() -> str:
    """Get admin username (from env or default in dev)"""
    if ADMIN_USERNAME:
        return ADMIN_USERNAME
    if not IS_PRODUCTION:
        return DEFAULT_DEV_USERNAME
    return ""  # Production without config


def verify_admin_password(username: str, password: str) -> bool:
    """
    Verify admin credentials.
    
    Production rules:
    - MUST have ADMIN_USERNAME and ADMIN_PASSWORD_HASH in env
    - Default credentials NEVER work
    
    Development rules:
    - If env vars set, use them
    - Otherwise, allow admin/admin123 for convenience
    """
    # Get expected username
    expected_username = get_admin_username()
    
    # Username check first
    if not expected_username or username != expected_username:
        return False
    
    # Production: REQUIRE proper hash, NEVER allow default password
    if IS_PRODUCTION:
        if not ADMIN_PASSWORD_HASH:
            return False
        # Block default password even if somehow username matched
        if password == DEFAULT_DEV_PASSWORD:
            return False
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                ADMIN_PASSWORD_HASH.encode('utf-8')
            )
        except Exception:
            return False
    
    # Development: check env hash if available, else allow default
    if ADMIN_PASSWORD_HASH:
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                ADMIN_PASSWORD_HASH.encode('utf-8')
            )
        except Exception:
            return False
    
    # Dev fallback: default credentials
    return password == DEFAULT_DEV_PASSWORD


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


def get_cookie_settings() -> dict:
    """Get cookie settings based on environment"""
    return {
        "key": COOKIE_NAME,
        "path": COOKIE_PATH,
        "httponly": True,
        "secure": COOKIE_SECURE,
        "samesite": COOKIE_SAMESITE,
        "max_age": COOKIE_MAX_AGE
    }


# ============== MOBILE AUTH HELPERS ==============

MOBILE_REFRESH_TOKEN_EXPIRE_DAYS = 30  # Longer for mobile convenience


def create_mobile_refresh_token(user_id: str, token_version: int = 0) -> Tuple[str, str]:
    """
    Create JWT refresh token for mobile with unique JTI.
    Returns: (token_string, jti)
    """
    jti = secrets.token_hex(16)
    expire = datetime.now(timezone.utc) + timedelta(days=MOBILE_REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "type": "mobile_refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": jti,
        "v": token_version
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, jti


def hash_token(token: str) -> str:
    """Hash a token for secure storage (SHA-256)"""
    return hashlib.sha256(token.encode()).hexdigest()


def get_mobile_refresh_expiry() -> datetime:
    """Get expiry datetime for mobile refresh token"""
    return datetime.now(timezone.utc) + timedelta(days=MOBILE_REFRESH_TOKEN_EXPIRE_DAYS)
