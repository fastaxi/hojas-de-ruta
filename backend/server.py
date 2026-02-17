"""
RutasFast - Main FastAPI Server
Backend for taxi route sheet management app
"""
from pathlib import Path
from dotenv import load_dotenv

# CRITICAL: Load .env BEFORE any local imports that read env vars
# NOTE: override=False ensures Kubernetes environment variables are NOT overwritten
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env', override=False)

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header, Query, Cookie, Request
from fastapi.responses import StreamingResponse, JSONResponse, Response
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument
from bson import ObjectId
import os
import logging
import re
import pytz
import asyncio
from typing import Optional, List
from datetime import datetime, timezone, timedelta, date
import io

# Local imports (AFTER load_dotenv)
from models import (
    User, UserCreate, UserUpdate, UserPublic,
    Driver, DriverCreate, DriverUpdate,
    RouteSheet, RouteSheetCreate, RouteSheetAnnul,
    AppConfig, AppConfigUpdate,
    LoginRequest, TokenResponse, RefreshRequest,
    ChangePasswordRequest,
    AdminLoginRequest,
    AssistanceCompany, AssistanceCompanyCreate
)
from auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    verify_admin_password, create_admin_token, get_cookie_settings,
    is_admin_configured, is_admin_env_configured, get_admin_username,
    ACCESS_TOKEN_EXPIRE_MINUTES, IS_PRODUCTION,
    create_mobile_refresh_token, hash_token, get_mobile_refresh_expiry,
    MOBILE_REFRESH_TOKEN_EXPIRE_DAYS
)
from dateutil.relativedelta import relativedelta
import secrets
import string

# MongoDB connection
# In production, MONGO_URL comes from Kubernetes secrets (Atlas MongoDB)
# In development sandbox, use localhost fallback
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="RutasFast API", version="1.0.0")

# Create routers
api_router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/auth", tags=["auth"])
mobile_auth_router = APIRouter(prefix="/auth/mobile", tags=["auth-mobile"])
user_router = APIRouter(prefix="/me", tags=["user"])
sheets_router = APIRouter(prefix="/route-sheets", tags=["route-sheets"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])
internal_router = APIRouter(prefix="/internal", tags=["internal"])

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Retention job token (for automated schedulers)
RETENTION_JOB_TOKEN = os.environ.get("RETENTION_JOB_TOKEN")

# ============== STARTUP STATE (for readiness) ==============
DB_CONNECTED = False
INDEXES_OK = False
MISSING_CRITICAL_INDEXES = []
LAST_INDEX_ERROR = None


# ============== INDEX CREATION HELPER ==============
async def _create_index(name: str, coro, critical: bool, failures_critical: list, failures_noncritical: list):
    """Create an index and track success/failure"""
    global LAST_INDEX_ERROR
    try:
        await coro
        logger.info(f"Index OK: {name}")
    except Exception as e:
        LAST_INDEX_ERROR = f"{name}: {str(e)}"
        msg = f"Index FAILED: {name} (critical={critical}) err={e}"
        if critical:
            logger.error(msg)
            failures_critical.append(name)
        else:
            logger.warning(msg)
            failures_noncritical.append(name)


# ============== STARTUP / SHUTDOWN ==============
@app.on_event("startup")
async def startup_db():
    """Initialize database connection and indexes with proper error handling"""
    global DB_CONNECTED, INDEXES_OK, MISSING_CRITICAL_INDEXES, LAST_INDEX_ERROR

    # Reset state
    DB_CONNECTED = False
    INDEXES_OK = False
    MISSING_CRITICAL_INDEXES = []
    LAST_INDEX_ERROR = None

    # ============== MONGODB RETRY ==============
    max_retries = 5
    retry_delay = 3

    for attempt in range(max_retries):
        try:
            await client.admin.command("ping")
            DB_CONNECTED = True
            logger.info(f"MongoDB connection successful (attempt {attempt + 1})")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"MongoDB connection attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error(f"Failed to connect to MongoDB after {max_retries} attempts: {e}")
                raise

    # ============== INDEX CREATION (NO SILENT PASS) ==============
    failures_critical = []
    failures_noncritical = []

    # USERS (non-critical - app works but slower queries)
    await _create_index("users_unique_email", 
        db.users.create_index("email", unique=True), 
        False, failures_critical, failures_noncritical)
    await _create_index("users_unique_id", 
        db.users.create_index("id", unique=True), 
        False, failures_critical, failures_noncritical)

    # DRIVERS (non-critical)
    await _create_index("drivers_user_id", 
        db.drivers.create_index("user_id"), 
        False, failures_critical, failures_noncritical)
    await _create_index("drivers_unique_id", 
        db.drivers.create_index("id", unique=True), 
        False, failures_critical, failures_noncritical)

    # ROUTE SHEETS - query indexes (non-critical)
    await _create_index("route_sheets_user_created_at", 
        db.route_sheets.create_index([("user_id", 1), ("created_at", -1)]), 
        False, failures_critical, failures_noncritical)
    await _create_index("route_sheets_user_pickup_datetime", 
        db.route_sheets.create_index([("user_id", 1), ("pickup_datetime", -1)]), 
        False, failures_critical, failures_noncritical)
    await _create_index("route_sheets_status", 
        db.route_sheets.create_index("status"), 
        False, failures_critical, failures_noncritical)
    await _create_index("route_sheets_user_visible", 
        db.route_sheets.create_index("user_visible"), 
        False, failures_critical, failures_noncritical)
    await _create_index("route_sheets_unique_id", 
        db.route_sheets.create_index("id", unique=True), 
        False, failures_critical, failures_noncritical)

    # ROUTE SHEETS - CRITICAL: unique numbering + TTL purge
    await _create_index("route_sheets_unique_user_year_seq",
        db.route_sheets.create_index([("user_id", 1), ("year", 1), ("seq_number", 1)], unique=True),
        True, failures_critical, failures_noncritical)
    await _create_index("route_sheets_ttl_purge_at",
        db.route_sheets.create_index("purge_at", expireAfterSeconds=0),
        True, failures_critical, failures_noncritical)

    # PASSWORD RESET TOKENS - CRITICAL TTL
    await _create_index("password_reset_tokens_unique_token_hash",
        db.password_reset_tokens.create_index("token_hash", unique=True),
        False, failures_critical, failures_noncritical)
    await _create_index("password_reset_tokens_ttl_expires_at",
        db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0),
        True, failures_critical, failures_noncritical)

    # COUNTERS - CRITICAL for atomic numbering
    await _create_index("counters_unique_user_year",
        db.counters.create_index([("user_id", 1), ("year", 1)], unique=True),
        True, failures_critical, failures_noncritical)

    # APP CONFIG INIT (not an index, but must run)
    try:
        existing_config = await db.app_config.find_one({"id": "global"}, {"_id": 0})
        if not existing_config:
            config = AppConfig()
            await db.app_config.insert_one(config.model_dump())
            logger.info("Initialized default app_config")
        elif "pdf_config_version" not in existing_config:
            await db.app_config.update_one({"id": "global"}, {"$set": {"pdf_config_version": 1}})
            logger.info("Added pdf_config_version to app_config")
    except Exception as e:
        LAST_INDEX_ERROR = f"app_config_init: {str(e)}"
        logger.error(f"Error initializing app_config: {e}")

    # RATE LIMITS - CRITICAL TTL
    await _create_index("rate_limits_ttl_expires_at",
        db.rate_limits.create_index("expires_at", expireAfterSeconds=0),
        True, failures_critical, failures_noncritical)
    await _create_index("rate_limits_user_action",
        db.rate_limits.create_index([("user_id", 1), ("action", 1)]),
        False, failures_critical, failures_noncritical)

    # PDF CACHE - CRITICAL TTL + unique
    await _create_index("pdf_cache_ttl_expires_at",
        db.pdf_cache.create_index("expires_at", expireAfterSeconds=0),
        True, failures_critical, failures_noncritical)
    await _create_index("pdf_cache_unique_sheet_config_status",
        db.pdf_cache.create_index([("sheet_id", 1), ("config_version", 1), ("status", 1)], unique=True),
        True, failures_critical, failures_noncritical)

    # MOBILE REFRESH TOKENS - CRITICAL TTL + unique
    await _create_index("mobile_refresh_tokens_unique_token_hash",
        db.mobile_refresh_tokens.create_index("token_hash", unique=True),
        True, failures_critical, failures_noncritical)
    await _create_index("mobile_refresh_tokens_unique_jti",
        db.mobile_refresh_tokens.create_index("jti", unique=True),
        False, failures_critical, failures_noncritical)
    await _create_index("mobile_refresh_tokens_user_id",
        db.mobile_refresh_tokens.create_index("user_id"),
        False, failures_critical, failures_noncritical)
    await _create_index("mobile_refresh_tokens_ttl_expires_at",
        db.mobile_refresh_tokens.create_index("expires_at", expireAfterSeconds=0),
        True, failures_critical, failures_noncritical)

    # Final readiness decision
    MISSING_CRITICAL_INDEXES = failures_critical
    INDEXES_OK = (len(failures_critical) == 0)

    if INDEXES_OK:
        logger.info("Startup OK: DB_CONNECTED=true, INDEXES_OK=true")
    else:
        logger.error(f"Startup DEGRADED: DB_CONNECTED={DB_CONNECTED}, INDEXES_OK=false, missing={MISSING_CRITICAL_INDEXES}")
        # Launch background retry task
        asyncio.create_task(retry_critical_indexes_forever())


async def retry_critical_indexes_forever():
    """Background task to retry creating critical indexes every 60s"""
    global INDEXES_OK, MISSING_CRITICAL_INDEXES, LAST_INDEX_ERROR
    
    while not INDEXES_OK:
        logger.warning("Retrying critical indexes in 60s...")
        await asyncio.sleep(60)
        
        try:
            failures_critical = []
            failures_noncritical = []
            
            # Retry only critical indexes
            await _create_index("route_sheets_unique_user_year_seq",
                db.route_sheets.create_index([("user_id", 1), ("year", 1), ("seq_number", 1)], unique=True),
                True, failures_critical, failures_noncritical)
            await _create_index("route_sheets_ttl_purge_at",
                db.route_sheets.create_index("purge_at", expireAfterSeconds=0),
                True, failures_critical, failures_noncritical)
            await _create_index("password_reset_tokens_ttl_expires_at",
                db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0),
                True, failures_critical, failures_noncritical)
            await _create_index("counters_unique_user_year",
                db.counters.create_index([("user_id", 1), ("year", 1)], unique=True),
                True, failures_critical, failures_noncritical)
            await _create_index("rate_limits_ttl_expires_at",
                db.rate_limits.create_index("expires_at", expireAfterSeconds=0),
                True, failures_critical, failures_noncritical)
            await _create_index("pdf_cache_ttl_expires_at",
                db.pdf_cache.create_index("expires_at", expireAfterSeconds=0),
                True, failures_critical, failures_noncritical)
            await _create_index("pdf_cache_unique_sheet_config_status",
                db.pdf_cache.create_index([("sheet_id", 1), ("config_version", 1), ("status", 1)], unique=True),
                True, failures_critical, failures_noncritical)
            await _create_index("mobile_refresh_tokens_unique_token_hash",
                db.mobile_refresh_tokens.create_index("token_hash", unique=True),
                True, failures_critical, failures_noncritical)
            await _create_index("mobile_refresh_tokens_ttl_expires_at",
                db.mobile_refresh_tokens.create_index("expires_at", expireAfterSeconds=0),
                True, failures_critical, failures_noncritical)
            
            MISSING_CRITICAL_INDEXES = failures_critical
            INDEXES_OK = (len(failures_critical) == 0)
            
            if INDEXES_OK:
                logger.info("Critical indexes recovered; readiness is now healthy")
        except Exception as e:
            logger.error(f"Critical index retry failed: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()


# Timezone for date filtering
MADRID_TZ = pytz.timezone('Europe/Madrid')


def date_to_utc_range(d: date) -> tuple[datetime, datetime]:
    """Convert a local date (Europe/Madrid) to UTC datetime range"""
    # Start of day in Madrid
    start_local = MADRID_TZ.localize(datetime(d.year, d.month, d.day, 0, 0, 0))
    # End of day in Madrid
    end_local = MADRID_TZ.localize(datetime(d.year, d.month, d.day, 23, 59, 59, 999999))
    # Convert to UTC
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


# ============== PDF RATE LIMITING ==============
PDF_RATE_LIMITS = {
    "pdf_individual": {"max_requests": 30, "window_minutes": 10},
    "pdf_range": {"max_requests": 10, "window_minutes": 10}
}


async def check_pdf_rate_limit(user_id: str, action: str) -> bool:
    """
    Check if user is within rate limit for PDF action.
    Returns True if allowed, raises HTTPException if blocked.
    Uses DB collection with TTL for distributed rate limiting.
    """
    limits = PDF_RATE_LIMITS.get(action)
    if not limits:
        return True
    
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=limits["window_minutes"])
    
    # Count requests in window
    count = await db.rate_limits.count_documents({
        "user_id": user_id,
        "action": action,
        "created_at": {"$gte": window_start}
    })
    
    if count >= limits["max_requests"]:
        raise HTTPException(
            status_code=429,
            detail=f"Límite de {limits['max_requests']} solicitudes de PDF por {limits['window_minutes']} minutos excedido. Intenta más tarde."
        )
    
    return True


async def record_pdf_request(user_id: str, action: str):
    """Record a PDF request for rate limiting"""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=PDF_RATE_LIMITS[action]["window_minutes"])
    
    await db.rate_limits.insert_one({
        "user_id": user_id,
        "action": action,
        "created_at": now,
        "expires_at": expires_at
    })


# ============== PDF CACHING ==============
# Keep the cache small: mobile devices already cache/share locally.
# Long TTL + large PDFs can explode Mongo storage.
PDF_CACHE_DAYS = 7


async def get_cached_pdf(sheet_id: str, config_version: int, status: str) -> Optional[bytes]:
    """Get cached PDF if exists, config version and status match"""
    cache = await db.pdf_cache.find_one({
        "sheet_id": sheet_id,
        "config_version": config_version,
        "status": status
    })
    
    if cache and cache.get("pdf_bytes"):
        return cache["pdf_bytes"]
    return None


async def cache_pdf(sheet_id: str, config_version: int, sheet_status: str, pdf_bytes: bytes):
    """Cache PDF bytes with TTL. Key is (sheet_id, config_version, status)"""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=PDF_CACHE_DAYS)
    
    await db.pdf_cache.update_one(
        {"sheet_id": sheet_id, "config_version": config_version, "status": sheet_status},
        {
            "$set": {
                "sheet_id": sheet_id,
                "config_version": config_version,
                "status": sheet_status,
                "pdf_bytes": pdf_bytes,
                "created_at": now,
                "expires_at": expires_at
            }
        },
        upsert=True
    )


async def invalidate_pdf_cache(sheet_id: str, status: str = None):
    """
    Invalidate cache for a specific sheet.
    If status is provided, only invalidate that status.
    Used when sheet is annulled to invalidate ACTIVE cache only.
    """
    query = {"sheet_id": sheet_id}
    if status:
        query["status"] = status
    await db.pdf_cache.delete_many(query)


# ============== DEPENDENCIES ==============
async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Validate access token and return user"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token no proporcionado")
    
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    
    if user["status"] != "APPROVED":
        raise HTTPException(
            status_code=403, 
            detail="Este usuario aun no ha sido verificado por el administrador."
        )
    
    return user


async def get_current_admin(authorization: Optional[str] = Header(None)) -> dict:
    """Validate admin token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token no proporcionado")
    
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    
    if not payload or payload.get("type") != "admin":
        raise HTTPException(status_code=401, detail="Token de administrador inválido")
    
    return {"role": "admin"}


# ============== ROOT ==============
@api_router.get("/")
async def root():
    return {"message": "RutasFast API v1.0", "status": "ok"}


def _get_git_commit() -> str:
    """Get git commit hash from VERSION file, env var, git command, or 'unknown'"""
    # 1. Try VERSION file (created during Save to GitHub)
    version_file = os.path.join(os.path.dirname(__file__), "VERSION")
    if os.path.exists(version_file):
        try:
            with open(version_file, "r") as f:
                commit = f.read().strip()
                if commit:
                    return commit
        except Exception:
            pass
    
    # 2. Try environment variable (set during deployment)
    commit = os.environ.get("GIT_COMMIT")
    if commit:
        return commit
    
    # 3. Try git rev-parse (works in dev/preview)
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    
    # 4. Fallback
    return "unknown"


@api_router.get("/version")
async def get_version():
    """API version info (no auth required)"""
    return {
        "service": "RutasFast API",
        "api_version": "1.0.0",
        "commit": _get_git_commit(),
        "deployed_at": datetime.now(timezone.utc).isoformat()
    }


@api_router.get("/health")
async def health_check():
    """Health check with service status (for /api/health)"""
    return {
        "status": "healthy" if (DB_CONNECTED and INDEXES_OK) else "degraded",
        "environment": "production" if IS_PRODUCTION else "development",
        "admin_configured": is_admin_configured(),
        "admin_env_configured": is_admin_env_configured(),
        "admin_username": get_admin_username(),
        "email_enabled": False,
        "db_connected": DB_CONNECTED,
        "indexes_ok": INDEXES_OK
    }


# ============== K8S PROBES (root level, no /api prefix) ==============
@app.get("/live")
async def liveness():
    """Liveness probe - always returns 200 if process is alive"""
    return {"status": "alive"}


@app.get("/health")
async def readiness():
    """Readiness probe - returns 503 if critical indexes missing"""
    status = "healthy" if (DB_CONNECTED and INDEXES_OK) else "degraded"
    payload = {
        "status": status,
        "db_connected": DB_CONNECTED,
        "indexes_ok": INDEXES_OK,
        "missing_critical_indexes": MISSING_CRITICAL_INDEXES,
        "last_index_error": LAST_INDEX_ERROR,
    }
    if DB_CONNECTED and INDEXES_OK:
        return payload
    return JSONResponse(status_code=503, content=payload)


# ============== AUTH ENDPOINTS ==============
@auth_router.post("/register", response_model=dict)
async def register(data: UserCreate):
    """Register new user - requires admin approval"""
    # Check if email exists
    existing = await db.users.find_one({"email": data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Este email ya está registrado")
    
    # Create user
    user = User(
        full_name=data.full_name,
        dni_cif=data.dni_cif,
        license_number=data.license_number,
        license_council=data.license_council,
        phone=data.phone,
        email=data.email,
        password_hash=hash_password(data.password),
        vehicle_brand=data.vehicle_brand,
        vehicle_model=data.vehicle_model,
        vehicle_plate=data.vehicle_plate,
        status="PENDING"
    )
    
    # Keep datetime fields as native datetime for MongoDB
    user_dict = user.model_dump()
    
    await db.users.insert_one(user_dict)
    
    # Create drivers if provided
    if data.drivers:
        for driver_data in data.drivers:
            driver = Driver(
                full_name=driver_data.full_name,
                dni=driver_data.dni,
                user_id=user.id
            )
            # Keep datetime as native
            driver_dict = driver.model_dump()
            await db.drivers.insert_one(driver_dict)
    
    logger.info(f"New user registered: {data.email}")
    return {
        "message": "Solicitud enviada. Pendiente de verificación por el administrador.",
        "user_id": user.id
    }


@auth_router.post("/login")
async def login(data: LoginRequest):
    """
    Login user - returns access token in JSON, sets refresh token in httpOnly cookie.
    Must be approved. Handles temp password expiry and must_change_password flag.
    """
    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    if user["status"] != "APPROVED":
        raise HTTPException(
            status_code=403,
            detail="Este usuario aun no ha sido verificado por el administrador."
        )
    
    # Check if temp password has expired
    must_change = user.get("must_change_password", False)
    temp_expires = user.get("temp_password_expires_at")
    
    if must_change and temp_expires:
        # Ensure temp_expires is timezone-aware UTC
        if isinstance(temp_expires, datetime):
            if temp_expires.tzinfo is None:
                temp_expires = temp_expires.replace(tzinfo=timezone.utc)
        elif isinstance(temp_expires, str):
            temp_expires = datetime.fromisoformat(temp_expires.replace('Z', '+00:00'))
        
        now_utc = datetime.now(timezone.utc)
        if now_utc > temp_expires:
            raise HTTPException(
                status_code=403,
                detail="Contraseña temporal expirada. Contacte con la Federación."
            )
    
    # Get or initialize token_version
    token_version = user.get("token_version", 0)
    
    access_token = create_access_token(user["id"], user["email"])
    refresh_token = create_refresh_token(user["id"], token_version)
    
    # Create response with access token in JSON
    response = JSONResponse(content={
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "must_change_password": must_change,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "dni_cif": user.get("dni_cif", ""),
            "license_number": user.get("license_number", ""),
            "license_council": user.get("license_council", ""),
            "phone": user.get("phone", ""),
            "vehicle_brand": user.get("vehicle_brand", ""),
            "vehicle_model": user.get("vehicle_model", ""),
            "vehicle_plate": user.get("vehicle_plate", ""),
            "vehicle_license_number": user.get("vehicle_license_number", ""),
            "status": user["status"],
            "must_change_password": must_change,
            "created_at": user.get("created_at").isoformat() if user.get("created_at") else None,
            "updated_at": user.get("updated_at").isoformat() if user.get("updated_at") else None
        }
    })
    
    # Set refresh token in httpOnly cookie
    cookie_settings = get_cookie_settings()
    response.set_cookie(
        value=refresh_token,
        **cookie_settings
    )
    
    logger.info(f"User logged in: {user['email']} (must_change_password: {must_change})")
    return response


@auth_router.post("/refresh")
async def refresh_tokens(
    refresh_token: Optional[str] = Cookie(None, alias="refresh_token")
):
    """
    Refresh access token using refresh token from httpOnly cookie.
    Returns new access token in JSON and rotates refresh token in cookie.
    """
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No hay sesión activa")
    
    payload = decode_token(refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    
    if user["status"] != "APPROVED":
        raise HTTPException(status_code=403, detail="Usuario no verificado")
    
    # Check token_version for revocation (logout invalidates all tokens)
    current_version = user.get("token_version", 0)
    token_version = payload.get("v", 0)
    
    if token_version < current_version:
        raise HTTPException(status_code=401, detail="Sesión revocada. Por favor, inicia sesión de nuevo.")
    
    # Create new tokens (rotation)
    access_token = create_access_token(user["id"], user["email"])
    new_refresh_token = create_refresh_token(user["id"], current_version)
    
    # Create response with access token in JSON - return COMPLETE user object
    response = JSONResponse(content={
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "dni_cif": user.get("dni_cif", ""),
            "license_number": user.get("license_number", ""),
            "license_council": user.get("license_council", ""),
            "phone": user.get("phone", ""),
            "vehicle_brand": user.get("vehicle_brand", ""),
            "vehicle_model": user.get("vehicle_model", ""),
            "vehicle_plate": user.get("vehicle_plate", ""),
            "vehicle_license_number": user.get("vehicle_license_number", ""),
            "status": user["status"],
            "created_at": user.get("created_at").isoformat() if user.get("created_at") else None,
            "updated_at": user.get("updated_at").isoformat() if user.get("updated_at") else None
        }
    })
    
    # Rotate refresh token in cookie
    cookie_settings = get_cookie_settings()
    response.set_cookie(
        value=new_refresh_token,
        **cookie_settings
    )
    
    return response


@auth_router.post("/logout")
async def logout(
    refresh_token: Optional[str] = Cookie(None, alias="refresh_token")
):
    """
    Logout user - invalidates all refresh tokens by incrementing token_version.
    Clears the refresh token cookie.
    """
    response = JSONResponse(content={"message": "Sesión cerrada correctamente"})
    
    # Clear the cookie regardless
    cookie_settings = get_cookie_settings()
    response.delete_cookie(
        key=cookie_settings["key"],
        path=cookie_settings["path"],
        httponly=cookie_settings["httponly"],
        secure=cookie_settings["secure"],
        samesite=cookie_settings["samesite"]
    )
    
    # If we have a valid token, increment user's token_version to invalidate all sessions
    if refresh_token:
        payload = decode_token(refresh_token)
        if payload and payload.get("type") == "refresh":
            user_id = payload.get("sub")
            if user_id:
                # Increment token_version - this invalidates ALL refresh tokens for this user
                await db.users.update_one(
                    {"id": user_id},
                    {"$inc": {"token_version": 1}}
                )
                logger.info(f"User logged out (all sessions invalidated): {user_id}")
    
    return response


@auth_router.post("/forgot-password")
async def forgot_password():
    """
    Password recovery via email is DISABLED.
    Users must contact the Federation (admin) for password reset.
    """
    raise HTTPException(
        status_code=410,
        detail="Recuperación por email no disponible. Contacte con la Federación."
    )


@auth_router.post("/reset-password")
async def reset_password():
    """
    Password reset via email token is DISABLED.
    Users must contact the Federation (admin) for password reset.
    """
    raise HTTPException(
        status_code=410,
        detail="Recuperación por email no disponible. Contacte con la Federación."
    )


# ============== MOBILE AUTH ENDPOINTS ==============
# These endpoints return refresh tokens in JSON (no cookies) for React Native/Expo apps.
# Refresh tokens are stored in DB with hash for secure rotation and revocation.

# Rate limiting for mobile login (in-memory)
from collections import defaultdict
import time as time_module

mobile_login_attempts = defaultdict(list)
MOBILE_LOGIN_MAX_ATTEMPTS = 10
MOBILE_LOGIN_WINDOW_SECONDS = 600  # 10 minutes


def check_mobile_login_rate_limit(key: str) -> bool:
    """Check if login attempt is allowed (10 attempts per 10 min)"""
    now = time_module.time()
    mobile_login_attempts[key] = [
        t for t in mobile_login_attempts[key] 
        if now - t < MOBILE_LOGIN_WINDOW_SECONDS
    ]
    return len(mobile_login_attempts[key]) < MOBILE_LOGIN_MAX_ATTEMPTS


def record_mobile_login_attempt(key: str):
    mobile_login_attempts[key].append(time_module.time())


@mobile_auth_router.post("/login")
async def mobile_login(data: LoginRequest, request: Request):
    """
    Mobile login - returns access_token AND refresh_token in JSON (no cookies).
    Refresh token is stored in DB with hash for secure rotation.
    """
    # Rate limiting by IP + email
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{data.email}"
    
    if not check_mobile_login_rate_limit(rate_key):
        raise HTTPException(
            status_code=429,
            detail="Demasiados intentos. Espera unos minutos."
        )
    
    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    
    if not user or not verify_password(data.password, user["password_hash"]):
        record_mobile_login_attempt(rate_key)
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    if user["status"] != "APPROVED":
        raise HTTPException(
            status_code=403,
            detail="Este usuario aun no ha sido verificado por el administrador."
        )
    
    # Check temp password expiry
    must_change = user.get("must_change_password", False)
    temp_expires = user.get("temp_password_expires_at")
    
    if must_change and temp_expires:
        if isinstance(temp_expires, datetime):
            if temp_expires.tzinfo is None:
                temp_expires = temp_expires.replace(tzinfo=timezone.utc)
        elif isinstance(temp_expires, str):
            temp_expires = datetime.fromisoformat(temp_expires.replace('Z', '+00:00'))
        
        if datetime.now(timezone.utc) > temp_expires:
            raise HTTPException(
                status_code=403,
                detail="Contraseña temporal expirada. Contacte con la Federación."
            )
    
    token_version = user.get("token_version", 0)
    
    # Create tokens
    access_token = create_access_token(user["id"], user["email"])
    refresh_token, jti = create_mobile_refresh_token(user["id"], token_version)
    
    # Store refresh token hash in DB (never store token in clear)
    await db.mobile_refresh_tokens.insert_one({
        "jti": jti,
        "user_id": user["id"],
        "token_hash": hash_token(refresh_token),
        "token_version": token_version,
        "created_at": datetime.now(timezone.utc),
        "expires_at": get_mobile_refresh_expiry(),
        "revoked": False,
        "replaced_by_jti": None
    })
    
    logger.info(f"Mobile login: {user['email']} (jti: {jti[:8]}...)")
    
    # Return tokens in JSON (NO cookie) - return COMPLETE user object
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_expires_in": MOBILE_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        "must_change_password": must_change,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "dni_cif": user.get("dni_cif", ""),
            "license_number": user.get("license_number", ""),
            "license_council": user.get("license_council", ""),
            "phone": user.get("phone", ""),
            "vehicle_brand": user.get("vehicle_brand", ""),
            "vehicle_model": user.get("vehicle_model", ""),
            "vehicle_plate": user.get("vehicle_plate", ""),
            "vehicle_license_number": user.get("vehicle_license_number", ""),
            "status": user["status"],
            "must_change_password": must_change,
            "created_at": user.get("created_at").isoformat() if user.get("created_at") else None,
            "updated_at": user.get("updated_at").isoformat() if user.get("updated_at") else None
        }
    }


class MobileRefreshRequest(BaseModel):
    refresh_token: str


@mobile_auth_router.post("/refresh")
async def mobile_refresh(data: MobileRefreshRequest):
    """
    Mobile refresh - rotates refresh token (one-time use).
    Returns new access_token and new refresh_token.
    Old refresh token is invalidated after use.
    """
    # Decode token
    payload = decode_token(data.refresh_token)
    
    if not payload or payload.get("type") != "mobile_refresh":
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    
    jti = payload.get("jti")
    user_id = payload.get("sub")
    token_version_in_token = payload.get("v", 0)
    
    if not jti or not user_id:
        raise HTTPException(status_code=401, detail="Token malformado")
    
    # Find token in DB by hash (atomic operation)
    token_hash = hash_token(data.refresh_token)
    token_doc = await db.mobile_refresh_tokens.find_one_and_update(
        {
            "token_hash": token_hash,
            "revoked": False,
            "replaced_by_jti": None  # Not already rotated
        },
        {"$set": {"revoked": True}},  # Mark as used atomically
        return_document=ReturnDocument.BEFORE
    )
    
    if not token_doc:
        # Token already used, revoked, or doesn't exist
        logger.warning(f"Mobile refresh attempted with invalid/used token (jti: {jti[:8] if jti else 'N/A'})")
        raise HTTPException(status_code=401, detail="Token inválido, expirado o ya utilizado")
    
    # Verify user exists and is approved
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    
    if user["status"] != "APPROVED":
        raise HTTPException(status_code=403, detail="Usuario no verificado")
    
    # Check token_version for global revocation (password change, etc.)
    current_version = user.get("token_version", 0)
    if token_version_in_token < current_version:
        logger.warning(f"Mobile refresh with outdated token_version for user {user_id}")
        raise HTTPException(status_code=401, detail="Sesión revocada. Por favor, inicia sesión de nuevo.")
    
    # Create new tokens
    new_access_token = create_access_token(user["id"], user["email"])
    new_refresh_token, new_jti = create_mobile_refresh_token(user["id"], current_version)
    
    # Store new refresh token
    await db.mobile_refresh_tokens.insert_one({
        "jti": new_jti,
        "user_id": user["id"],
        "token_hash": hash_token(new_refresh_token),
        "token_version": current_version,
        "created_at": datetime.now(timezone.utc),
        "expires_at": get_mobile_refresh_expiry(),
        "revoked": False,
        "replaced_by_jti": None
    })
    
    # Update old token with replacement reference
    await db.mobile_refresh_tokens.update_one(
        {"jti": jti},
        {"$set": {"replaced_by_jti": new_jti}}
    )
    
    logger.info(f"Mobile refresh rotated: {jti[:8]}... -> {new_jti[:8]}...")
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_expires_in": MOBILE_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "dni_cif": user.get("dni_cif", ""),
            "license_number": user.get("license_number", ""),
            "license_council": user.get("license_council", ""),
            "phone": user.get("phone", ""),
            "vehicle_brand": user.get("vehicle_brand", ""),
            "vehicle_model": user.get("vehicle_model", ""),
            "vehicle_plate": user.get("vehicle_plate", ""),
            "vehicle_license_number": user.get("vehicle_license_number", ""),
            "status": user["status"],
            "created_at": user.get("created_at").isoformat() if user.get("created_at") else None,
            "updated_at": user.get("updated_at").isoformat() if user.get("updated_at") else None
        }
    }


class MobileLogoutRequest(BaseModel):
    refresh_token: str


@mobile_auth_router.post("/logout")
async def mobile_logout(data: MobileLogoutRequest):
    """
    Mobile logout - revokes the specific refresh token.
    Client should also delete the token from SecureStore.
    """
    payload = decode_token(data.refresh_token)
    
    if payload and payload.get("type") == "mobile_refresh":
        token_hash = hash_token(data.refresh_token)
        result = await db.mobile_refresh_tokens.update_one(
            {"token_hash": token_hash},
            {"$set": {"revoked": True}}
        )
        if result.modified_count > 0:
            logger.info(f"Mobile logout: token revoked (jti: {payload.get('jti', 'N/A')[:8]}...)")
    
    return {"message": "Sesión cerrada correctamente"}


# ============== USER ENDPOINTS ==============
@user_router.get("", response_model=UserPublic)
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user profile"""
    return UserPublic(**user)


@user_router.put("", response_model=UserPublic)
async def update_me(data: UserUpdate, user: dict = Depends(get_current_user)):
    """Update current user profile"""
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc)  # datetime, not string
        await db.users.update_one({"id": user["id"]}, {"$set": update_data})
    
    updated_user = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return UserPublic(**updated_user)


@user_router.get("/drivers", response_model=List[dict])
async def get_my_drivers(user: dict = Depends(get_current_user)):
    """Get current user's drivers"""
    drivers = await db.drivers.find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).to_list(100)
    return drivers


@user_router.post("/drivers", response_model=dict)
async def create_driver(data: DriverCreate, user: dict = Depends(get_current_user)):
    """Add a new driver"""
    driver = Driver(
        full_name=data.full_name,
        dni=data.dni,
        user_id=user["id"]
    )
    # Keep datetime as native
    driver_dict = driver.model_dump()
    await db.drivers.insert_one(driver_dict)
    return {"id": driver.id, "message": "Chofer añadido"}


@user_router.put("/drivers/{driver_id}", response_model=dict)
async def update_driver(
    driver_id: str,
    data: DriverUpdate,
    user: dict = Depends(get_current_user)
):
    """Update a driver - only provided fields are updated"""
    # Build update dict with only provided fields
    update_fields = {}
    if data.full_name is not None:
        update_fields["full_name"] = data.full_name
    if data.dni is not None:
        update_fields["dni"] = data.dni
    
    result = await db.drivers.update_one(
        {"id": driver_id, "user_id": user["id"]},
        {"$set": update_fields}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Chofer no encontrado")
    return {"message": "Chofer actualizado"}


@user_router.delete("/drivers/{driver_id}")
async def delete_driver(driver_id: str, user: dict = Depends(get_current_user)):
    """Delete a driver"""
    result = await db.drivers.delete_one({"id": driver_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Chofer no encontrado")
    return {"message": "Chofer eliminado"}


# ============== ASSISTANCE COMPANIES CRUD ==============
@user_router.get("/assistance-companies", response_model=List[dict])
async def get_my_assistance_companies(user: dict = Depends(get_current_user)):
    """Get current user's assistance companies"""
    companies = await db.assistance_companies.find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).sort("name", 1).to_list(100)
    return companies


@user_router.post("/assistance-companies", response_model=dict)
async def create_assistance_company(data: AssistanceCompanyCreate, user: dict = Depends(get_current_user)):
    """Add a new assistance company"""
    company = AssistanceCompany(
        name=data.name,
        cif=data.cif,
        contact_phone=data.contact_phone,
        contact_email=data.contact_email,
        user_id=user["id"]
    )
    company_dict = company.model_dump()
    await db.assistance_companies.insert_one(company_dict)
    return {"id": company.id, "message": "Empresa de asistencia añadida"}


@user_router.put("/assistance-companies/{company_id}", response_model=dict)
async def update_assistance_company(
    company_id: str,
    data: AssistanceCompanyCreate,
    user: dict = Depends(get_current_user)
):
    """Update an assistance company"""
    update_fields = {
        "name": data.name,
        "cif": data.cif,
        "contact_phone": data.contact_phone,
        "contact_email": data.contact_email
    }
    
    result = await db.assistance_companies.update_one(
        {"id": company_id, "user_id": user["id"]},
        {"$set": update_fields}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return {"message": "Empresa actualizada"}


@user_router.delete("/assistance-companies/{company_id}")
async def delete_assistance_company(company_id: str, user: dict = Depends(get_current_user)):
    """Delete an assistance company"""
    result = await db.assistance_companies.delete_one({"id": company_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return {"message": "Empresa eliminada"}


@user_router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    response: JSONResponse,
    user: dict = Depends(get_current_user)
):
    """
    Change user password.
    If must_change_password is true, this clears the flag.
    SECURITY: Invalidates all sessions by incrementing token_version and clearing refresh cookie.
    """
    # Verify current password
    if not verify_password(data.current_password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")
    
    # Validate new password (min 8 chars, 1 uppercase, 1 number)
    new_pass = data.new_password
    if len(new_pass) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres")
    if not any(c.isupper() for c in new_pass):
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos una mayúscula")
    if not any(c.isdigit() for c in new_pass):
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos un número")
    
    # Update password, clear flags, and INCREMENT token_version to invalidate all sessions
    new_hash = hash_password(new_pass)
    now = datetime.now(timezone.utc)
    
    await db.users.update_one(
        {"id": user["id"]},
        {
            "$set": {
                "password_hash": new_hash,
                "must_change_password": False,
                "temp_password_expires_at": None,
                "updated_at": now
            },
            "$inc": {"token_version": 1}  # Invalidate ALL refresh tokens
        }
    )
    
    logger.info(f"Password changed for user {user['id']} - all sessions invalidated")
    
    # Build response with cookie clearing
    result = JSONResponse(content={
        "message": "Contraseña actualizada. Vuelve a iniciar sesión.",
        "session_invalidated": True
    })
    
    # Clear refresh token cookie
    cookie_settings = get_cookie_settings()
    result.delete_cookie(
        key=cookie_settings["key"],
        path=cookie_settings["path"],
        httponly=cookie_settings["httponly"],
        secure=cookie_settings["secure"],
        samesite=cookie_settings["samesite"]
    )
    
    return result


# ============== ROUTE SHEETS ENDPOINTS ==============
@sheets_router.post("", response_model=dict)
async def create_route_sheet(
    data: RouteSheetCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new route sheet (closed upon save, never editable)"""
    # ============== VALIDATIONS ==============
    # 1. Contractor phone OR email required
    if not data.contractor_phone and not data.contractor_email:
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar teléfono o email del contratante"
        )
    
    assistance_snapshot = None
    
    # 2. Validation based on pickup_type
    if data.pickup_type == "AIRPORT":
        # Flight number required and validated
        if not data.flight_number:
            raise HTTPException(
                status_code=400,
                detail="Número de vuelo obligatorio para recogida en aeropuerto"
            )
        # Normalize: uppercase, remove spaces/hyphens
        fn_normalized = re.sub(r'[\s-]+', '', data.flight_number.strip().upper())
        # Validate: only alphanumeric, max 10 chars, must contain at least one digit
        if not re.match(r'^[A-Z0-9]{1,10}$', fn_normalized) or not re.search(r'\d', fn_normalized):
            raise HTTPException(
                status_code=400,
                detail="Formato de vuelo inválido. Ejemplos: VY1234, QF9, 1234, TP-217A"
            )
        # Store normalized value
        data.flight_number = fn_normalized
        # Force pickup_address to Aeropuerto de Asturias
        data.pickup_address = "Aeropuerto de Asturias"
    
    elif data.pickup_type == "OTHER":
        # Pickup address required
        if not data.pickup_address or not data.pickup_address.strip():
            raise HTTPException(
                status_code=400,
                detail="Dirección de recogida obligatoria"
            )
        # flight_number not allowed
        if data.flight_number:
            raise HTTPException(
                status_code=400,
                detail="Número de vuelo no aplica para este tipo de recogida"
            )
    
    elif data.pickup_type == "ROADSIDE":
        # Pickup address required (location of breakdown)
        if not data.pickup_address or not data.pickup_address.strip():
            raise HTTPException(
                status_code=400,
                detail="Ubicación de la asistencia obligatoria"
            )
        # Assistance company required
        if not data.assistance_company_id:
            raise HTTPException(
                status_code=400,
                detail="Debe seleccionar una empresa de asistencia"
            )
        # Verify company belongs to user and get snapshot
        company = await db.assistance_companies.find_one({
            "id": data.assistance_company_id,
            "user_id": user["id"]
        }, {"_id": 0})
        if not company:
            raise HTTPException(
                status_code=400,
                detail="Empresa de asistencia no encontrada"
            )
        # Create immutable snapshot
        assistance_snapshot = {
            "name": company["name"],
            "cif": company["cif"],
            "contact_phone": company.get("contact_phone"),
            "contact_email": company.get("contact_email")
        }
        # flight_number not allowed
        if data.flight_number:
            raise HTTPException(
                status_code=400,
                detail="Número de vuelo no aplica para asistencia en carretera"
            )

    # 3. Validate conductor driver belongs to the user (if provided)
    if data.conductor_driver_id:
        driver = await db.drivers.find_one(
            {"id": data.conductor_driver_id, "user_id": user["id"]},
            {"_id": 0}
        )
        if not driver:
            raise HTTPException(
                status_code=400,
                detail="Conductor seleccionado no encontrado"
            )
    
    # ============== ATOMIC NUMBERING ==============
    # Use local year (Europe/Madrid) to avoid edge cases around New Year.
    current_year = datetime.now(MADRID_TZ).year
    
    # findOneAndUpdate with $inc is atomic - no race conditions
    # ReturnDocument.AFTER ensures we get the incremented value
    counter_result = await db.counters.find_one_and_update(
        {"user_id": user["id"], "year": current_year},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    next_seq = counter_result["seq"]
    
    # ============== RETENTION DATES ==============
    # Use relativedelta for precise calendar months (not 30-day approximation)
    config = await db.app_config.find_one({"id": "global"}, {"_id": 0})
    hide_months = config.get("hide_after_months", 14) if config else 14
    purge_months = config.get("purge_after_months", 24) if config else 24
    
    now = datetime.now(timezone.utc)
    hide_at = now + relativedelta(months=+hide_months)
    purge_at = now + relativedelta(months=+purge_months)
    
    # ============== CREATE SHEET ==============
    # Convert pickup_datetime from ISO string to datetime for MongoDB filtering
    pickup_dt_str = data.pickup_datetime
    try:
        # Parse ISO datetime string and ensure UTC
        if 'Z' in pickup_dt_str:
            pickup_dt = datetime.fromisoformat(pickup_dt_str.replace('Z', '+00:00'))
        elif '+' in pickup_dt_str or pickup_dt_str.count('-') > 2:
            pickup_dt = datetime.fromisoformat(pickup_dt_str)
        else:
            # Assume local time (Europe/Madrid), convert to UTC
            naive_dt = datetime.fromisoformat(pickup_dt_str)
            local_dt = MADRID_TZ.localize(naive_dt)
            pickup_dt = local_dt.astimezone(timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha/hora inválido")
    
    # Build sheet data
    sheet_data = data.model_dump()
    # Remove assistance_company_id (we store snapshot instead)
    sheet_data.pop('assistance_company_id', None)
    
    sheet = RouteSheet(
        user_id=user["id"],
        year=current_year,
        seq_number=next_seq,
        hide_at=hide_at,
        purge_at=purge_at,
        assistance_company_snapshot=assistance_snapshot,
        **sheet_data
    )
    
    # Keep datetimes as native Python datetime for MongoDB BSON Date storage
    # TTL indexes require BSON Date, not ISO strings
    sheet_dict = sheet.model_dump()
    # CRITICAL: Store pickup_datetime as datetime object for date range queries
    sheet_dict["pickup_datetime"] = pickup_dt
    # created_at, hide_at, purge_at remain as datetime objects
    
    try:
        await db.route_sheets.insert_one(sheet_dict)
    except Exception as e:
        # Unique index violation shouldn't happen with atomic counter, but safety check
        if "duplicate key" in str(e).lower():
            logger.error(f"Duplicate sheet number {next_seq}/{current_year} for user {user['id']}")
            raise HTTPException(status_code=500, detail="Error de numeración, reintente")
        raise
    
    # Format: 001/2026, 1000/2026 (natural expansion beyond 999)
    sheet_number = f"{next_seq:03d}/{current_year}"
    logger.info(f"Route sheet created: {sheet_number} for user {user['id']}")
    
    return {
        "id": sheet.id,
        "sheet_number": sheet_number,
        "message": "Hoja de ruta creada"
    }


@sheets_router.get("", response_model=dict)
async def get_route_sheets(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    include_annulled: bool = False,
    limit: int = Query(default=50, le=200),
    cursor: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Get user's route sheets with filters and pagination.
    - Filters by pickup_datetime (not created_at)
    - Always filters user_visible=true
    - Excludes annulled by default
    - Cursor pagination by _id
    """
    # Base query: always user_visible=true for user endpoints
    query = {"user_id": user["id"], "user_visible": True}
    
    # Exclude annulled by default
    if not include_annulled:
        query["status"] = "ACTIVE"
    
    # Date range filter on pickup_datetime (converted to UTC from Europe/Madrid)
    if from_date or to_date:
        pickup_filter = {}
        if from_date:
            from_start, _ = date_to_utc_range(from_date)
            pickup_filter["$gte"] = from_start
        if to_date:
            _, to_end = date_to_utc_range(to_date)
            pickup_filter["$lte"] = to_end
        if pickup_filter:
            query["pickup_datetime"] = pickup_filter
    
    # Cursor pagination (by _id for stability)
    if cursor:
        try:
            query["_id"] = {"$lt": ObjectId(cursor)}
        except:
            pass  # Invalid cursor, ignore
    
    # Query with stable sort: year desc, seq_number desc (ordenado por número de hoja)
    sheets = await db.route_sheets.find(
        query
    ).sort([("year", -1), ("seq_number", -1), ("_id", -1)]).limit(limit).to_list(limit)
    
    # Build response
    result_sheets = []
    next_cursor = None
    
    for sheet in sheets:
        # Store _id for cursor before removing
        sheet_id = sheet.pop("_id")
        next_cursor = str(sheet_id)
        sheet["sheet_number"] = f"{sheet['seq_number']:03d}/{sheet['year']}"
        result_sheets.append(sheet)
    
    return {
        "sheets": result_sheets,
        "next_cursor": next_cursor if len(result_sheets) == limit else None,
        "count": len(result_sheets)
    }


@sheets_router.get("/{sheet_id}", response_model=dict)
async def get_route_sheet(sheet_id: str, user: dict = Depends(get_current_user)):
    """Get a specific route sheet (only if user_visible=true)"""
    sheet = await db.route_sheets.find_one(
        {"id": sheet_id, "user_id": user["id"], "user_visible": True},
        {"_id": 0}
    )
    if not sheet:
        raise HTTPException(status_code=404, detail="Hoja no encontrada")
    
    sheet["sheet_number"] = f"{sheet['seq_number']:03d}/{sheet['year']}"
    return sheet


@sheets_router.post("/{sheet_id}/annul")
async def annul_route_sheet(
    sheet_id: str,
    data: RouteSheetAnnul,
    user: dict = Depends(get_current_user)
):
    """Annul a route sheet (soft delete)"""
    sheet = await db.route_sheets.find_one(
        {"id": sheet_id, "user_id": user["id"]},
        {"_id": 0}
    )
    
    if not sheet:
        raise HTTPException(status_code=404, detail="Hoja no encontrada")
    
    if sheet["status"] == "ANNULLED":
        raise HTTPException(status_code=400, detail="La hoja ya está anulada")
    
    await db.route_sheets.update_one(
        {"id": sheet_id},
        {"$set": {
            "status": "ANNULLED",
            "annulled_at": datetime.now(timezone.utc),  # datetime
            "annul_reason": data.reason
        }}
    )
    
    # Invalidate only ACTIVE cache - ANNULLED will be cached separately
    await invalidate_pdf_cache(sheet_id, status="ACTIVE")
    
    return {"message": "Hoja anulada correctamente"}


@sheets_router.get("/{sheet_id}/pdf")
async def get_route_sheet_pdf(sheet_id: str, user: dict = Depends(get_current_user)):
    """
    Generate PDF for a single route sheet.
    - Rate limited: 30 requests per 10 minutes per user
    - Cached: PDF cached for 7 days (both ACTIVE and ANNULLED), invalidated on config change
      (Short TTL to prevent MongoDB storage growth with large PDFs)
    - Only returns user_visible=true sheets
    """
    # Check rate limit
    await check_pdf_rate_limit(user["id"], "pdf_individual")
    
    sheet = await db.route_sheets.find_one(
        {"id": sheet_id, "user_id": user["id"], "user_visible": True},
        {"_id": 0}
    )
    if not sheet:
        raise HTTPException(status_code=404, detail="Hoja no encontrada")
    
    # Get config for PDF headers and version
    config = await db.app_config.find_one({"id": "global"}, {"_id": 0})
    if not config:
        config = AppConfig().model_dump()
    
    config_version = config.get("pdf_config_version", 1)
    sheet_status = sheet["status"]
    
    # Check cache (both ACTIVE and ANNULLED are cached)
    cached_pdf = await get_cached_pdf(sheet_id, config_version, sheet_status)
    if cached_pdf:
        # Record request for rate limiting
        await record_pdf_request(user["id"], "pdf_individual")
        
        sheet_number = f"{sheet['seq_number']:03d}_{sheet['year']}"
        filename = f"hoja_ruta_{sheet_number}.pdf"
        
        return Response(
            content=cached_pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\"",
                "Cache-Control": "private, max-age=86400",
                "X-Content-Type-Options": "nosniff",
                "X-Cache": "HIT"
            }
        )
    
    # Get user full data
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    
    # Get driver name if not titular
    driver_name = "Titular"
    if sheet.get("conductor_driver_id"):
        driver = await db.drivers.find_one(
            {"id": sheet["conductor_driver_id"], "user_id": sheet["user_id"]},
            {"_id": 0}
        )
        if driver:
            driver_name = driver["full_name"]
    
    # Generate PDF (includes watermark for ANNULLED)
    from pdf_generator import generate_route_sheet_pdf
    pdf_buffer = await asyncio.to_thread(generate_route_sheet_pdf, sheet, user_data, config, driver_name)
    pdf_bytes = pdf_buffer.getvalue()
    
    # Cache the PDF (both ACTIVE and ANNULLED)
    await cache_pdf(sheet_id, config_version, sheet_status, pdf_bytes)
    
    # Record request for rate limiting
    await record_pdf_request(user["id"], "pdf_individual")
    
    sheet_number = f"{sheet['seq_number']:03d}_{sheet['year']}"
    filename = f"hoja_ruta_{sheet_number}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"",
            "Cache-Control": "private, max-age=86400",
            "X-Content-Type-Options": "nosniff",
            "X-Cache": "MISS"
        }
    )


@sheets_router.get("/pdf/range")
async def get_route_sheets_pdf_range(
    from_date: date,
    to_date: date,
    user: dict = Depends(get_current_user)
):
    """
    Generate PDF for multiple route sheets in date range.
    - Rate limited: 10 requests per 10 minutes per user
    - Filters by pickup_datetime (Europe/Madrid to UTC)
    - Always user_visible=true
    - Never includes annulled sheets
    """
    # Check rate limit
    await check_pdf_rate_limit(user["id"], "pdf_range")
    
    # Convert dates to UTC range
    from_start, _ = date_to_utc_range(from_date)
    _, to_end = date_to_utc_range(to_date)
    
    query = {
        "user_id": user["id"],
        "user_visible": True,
        "status": "ACTIVE",  # Never include annulled in range PDF
        "pickup_datetime": {"$gte": from_start, "$lte": to_end}
    }
    
    sheets = await db.route_sheets.find(
        query,
        {"_id": 0}
    ).sort("pickup_datetime", 1).to_list(1000)
    
    if not sheets:
        raise HTTPException(status_code=404, detail="No hay hojas en el rango seleccionado")
    
    # Get config and user data
    config = await db.app_config.find_one({"id": "global"}, {"_id": 0})
    if not config:
        config = AppConfig().model_dump()
    
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    
    # Get all drivers for this user
    drivers = await db.drivers.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    drivers_map = {d["id"]: d["full_name"] for d in drivers}
    
    # Generate multi-page PDF
    from pdf_generator import generate_multi_sheet_pdf
    pdf_buffer = await asyncio.to_thread(generate_multi_sheet_pdf, sheets, user_data, config, drivers_map)
    pdf_bytes = pdf_buffer.getvalue()
    
    # Record request for rate limiting
    await record_pdf_request(user["id"], "pdf_range")
    
    filename = f"hojas_ruta_{from_date}_a_{to_date}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff"
        }
    )


# ============== ADMIN ENDPOINTS ==============

# Rate limiting for admin login (in-memory, simple implementation)
# For production with multiple instances, use Redis
from collections import defaultdict
import time

admin_login_attempts = defaultdict(list)  # IP -> list of timestamps
ADMIN_LOGIN_MAX_ATTEMPTS = 5
ADMIN_LOGIN_LOCKOUT_SECONDS = 300  # 5 minutes


def check_admin_rate_limit(ip: str) -> bool:
    """Check if IP is rate limited. Returns True if allowed, False if blocked."""
    now = time.time()
    # Clean old attempts
    admin_login_attempts[ip] = [
        t for t in admin_login_attempts[ip] 
        if now - t < ADMIN_LOGIN_LOCKOUT_SECONDS
    ]
    return len(admin_login_attempts[ip]) < ADMIN_LOGIN_MAX_ATTEMPTS


def record_admin_login_attempt(ip: str):
    """Record a failed login attempt"""
    admin_login_attempts[ip].append(time.time())


def clear_admin_login_attempts(ip: str):
    """Clear attempts after successful login"""
    admin_login_attempts[ip] = []


@admin_router.post("/login")
async def admin_login(data: AdminLoginRequest, request: Request):
    """
    Admin login with rate limiting and fail-closed in production.
    
    Production requirements:
    - ADMIN_USERNAME and ADMIN_PASSWORD_HASH must be set in environment
    - Default credentials (admin/admin123) are NEVER accepted
    
    Rate limiting:
    - 5 failed attempts per IP = 5 minute lockout
    """
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    
    # Check rate limit first
    if not check_admin_rate_limit(client_ip):
        logger.warning(f"Admin login rate limited: {client_ip}")
        raise HTTPException(
            status_code=429,
            detail="Demasiados intentos. Espera 5 minutos."
        )
    
    # Check if admin is configured (fail-closed in production)
    if not is_admin_configured():
        logger.error("Admin login attempted but admin not configured in production")
        raise HTTPException(
            status_code=503,
            detail="Administrador no configurado. Contacte al administrador del sistema."
        )
    
    # Verify credentials
    if not verify_admin_password(data.username, data.password):
        record_admin_login_attempt(client_ip)
        remaining = ADMIN_LOGIN_MAX_ATTEMPTS - len(admin_login_attempts[client_ip])
        logger.warning(f"Failed admin login attempt from {client_ip} ({remaining} attempts remaining)")
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    # Success - clear rate limit and create token
    clear_admin_login_attempts(client_ip)
    token = create_admin_token()
    logger.info(f"Admin login successful from {client_ip}")
    return {"access_token": token, "token_type": "bearer"}


@admin_router.get("/users", response_model=List[dict])
async def admin_get_users(
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    admin: dict = Depends(get_current_admin)
):
    """Get all users (admin) with pagination"""
    query = {}
    
    if status:
        query["status"] = status
    
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"dni_cif": {"$regex": search, "$options": "i"}}
        ]
    
    users = await db.users.find(
        query,
        {"_id": 0, "password_hash": 0}
    ).sort("created_at", -1).skip(offset).limit(limit).to_list(limit)
    
    return users


@admin_router.get("/users/count")
async def admin_get_users_count(
    status: Optional[str] = None,
    search: Optional[str] = None,
    admin: dict = Depends(get_current_admin)
):
    """Get total user count for pagination"""
    query = {}
    
    if status:
        query["status"] = status
    
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"dni_cif": {"$regex": search, "$options": "i"}}
        ]
    
    count = await db.users.count_documents(query)
    return {"count": count}


@admin_router.get("/users/{user_id}", response_model=dict)
async def admin_get_user(user_id: str, admin: dict = Depends(get_current_admin)):
    """Get user details (admin)"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Get drivers
    drivers = await db.drivers.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    user["drivers"] = drivers
    
    return user


@admin_router.put("/users/{user_id}", response_model=dict)
async def admin_update_user(
    user_id: str,
    data: UserUpdate,
    admin: dict = Depends(get_current_admin)
):
    """Update user (admin)"""
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc)  # datetime
        result = await db.users.update_one({"id": user_id}, {"$set": update_data})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return {"message": "Usuario actualizado"}


@admin_router.post("/users/{user_id}/approve")
async def admin_approve_user(user_id: str, admin: dict = Depends(get_current_admin)):
    """Approve user registration (no email notification)"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if user["status"] == "APPROVED":
        raise HTTPException(status_code=400, detail="Usuario ya está aprobado")
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "status": "APPROVED",
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    logger.info(f"User approved: {user['email']}")
    
    return {
        "message": "Usuario aprobado",
        "user_email": user["email"],
        "user_name": user["full_name"]
    }


def generate_temp_password(length: int = 14) -> str:
    """Generate a random temporary password (letters, digits, safe symbols)"""
    alphabet = string.ascii_letters + string.digits
    # Ensure at least one uppercase, one lowercase, one digit
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
    ]
    password += [secrets.choice(alphabet) for _ in range(length - 3)]
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)


@admin_router.post("/users/{user_id}/reset-password-temp")
async def admin_reset_password_temp(
    user_id: str, 
    request: Request,
    admin: dict = Depends(get_current_admin)
):
    """
    Generate temporary password for user (72h expiry).
    User must change password on next login.
    The temporary password is returned ONLY in this response - it is NOT stored in plain text.
    """
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Generate temp password
    temp_password = generate_temp_password(14)
    temp_hash = hash_password(temp_password)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=72)
    
    # Update user with temp password
    await db.users.update_one(
        {"id": user_id},
        {
            "$set": {
                "password_hash": temp_hash,
                "must_change_password": True,
                "temp_password_expires_at": expires_at,
                "updated_at": now
            }
        }
    )
    
    # Get client IP (behind proxy)
    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    
    # Audit log (NEVER include password)
    audit_entry = {
        "action": "RESET_PASSWORD_TEMP",
        "admin_username": get_admin_username(),
        "user_id": user_id,
        "user_email": user["email"],
        "user_name": user["full_name"],
        "timestamp": now,
        "expires_at": expires_at,
        "client_ip": client_ip
    }
    await db.admin_audit_logs.insert_one(audit_entry)
    
    logger.info(f"Temp password generated for user {user_id} by admin (expires: {expires_at.isoformat()})")
    
    # Return temp password ONLY HERE - not logged, not stored
    return {
        "message": "Contraseña temporal generada",
        "temp_password": temp_password,  # SHOWN ONLY ONCE
        "expires_at": expires_at.isoformat(),
        "expires_in_hours": 72,
        "user_email": user["email"],
        "user_name": user["full_name"]
    }


@admin_router.get("/audit/password-resets")
async def admin_get_password_reset_audit(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(default=20, le=100),
    cursor: Optional[str] = Query(None, description="Cursor for pagination (timestamp ISO)"),
    admin: dict = Depends(get_current_admin)
):
    """
    Get password reset audit logs.
    Returns list of reset events sorted by timestamp (newest first).
    """
    query = {"action": "RESET_PASSWORD_TEMP"}
    
    if user_id:
        query["user_id"] = user_id
    
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor.replace("Z", "+00:00"))
            query["timestamp"] = {"$lt": cursor_dt}
        except ValueError:
            pass
    
    logs = await db.admin_audit_logs.find(
        query,
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    # Convert datetime to ISO string
    for log in logs:
        if isinstance(log.get("timestamp"), datetime):
            log["timestamp"] = log["timestamp"].isoformat()
        if isinstance(log.get("expires_at"), datetime):
            log["expires_at"] = log["expires_at"].isoformat()
    
    # Next cursor
    next_cursor = None
    if len(logs) == limit and logs:
        next_cursor = logs[-1]["timestamp"]
    
    return {
        "items": logs,
        "next_cursor": next_cursor,
        "count": len(logs)
    }


@admin_router.get("/users/{user_id}/audit/password-resets")
async def admin_get_user_password_reset_audit(
    user_id: str,
    limit: int = Query(default=10, le=50),
    admin: dict = Depends(get_current_admin)
):
    """
    Get password reset audit logs for a specific user.
    """
    logs = await db.admin_audit_logs.find(
        {"action": "RESET_PASSWORD_TEMP", "user_id": user_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    # Convert datetime to ISO string
    for log in logs:
        if isinstance(log.get("timestamp"), datetime):
            log["timestamp"] = log["timestamp"].isoformat()
        if isinstance(log.get("expires_at"), datetime):
            log["expires_at"] = log["expires_at"].isoformat()
    
    return logs


@admin_router.get("/route-sheets/{sheet_id}/pdf")
async def admin_get_route_sheet_pdf(
    sheet_id: str,
    admin: dict = Depends(get_current_admin)
):
    """
    Generate PDF for a route sheet (admin access).
    - No user_visible filter (admin sees all)
    - Reuses PDF cache
    """
    sheet = await db.route_sheets.find_one({"id": sheet_id}, {"_id": 0})
    if not sheet:
        raise HTTPException(status_code=404, detail="Hoja no encontrada")
    
    # Get config for PDF headers and version
    config = await db.app_config.find_one({"id": "global"}, {"_id": 0})
    if not config:
        config = AppConfig().model_dump()
    
    config_version = config.get("pdf_config_version", 1)
    sheet_status = sheet["status"]
    
    # Check cache
    cached_pdf = await get_cached_pdf(sheet_id, config_version, sheet_status)
    if cached_pdf:
        sheet_number = f"{sheet['seq_number']:03d}_{sheet['year']}"
        filename = f"hoja_ruta_{sheet_number}.pdf"
        
        return Response(
            content=cached_pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\"",
                "Cache-Control": "private, max-age=86400",
                "X-Content-Type-Options": "nosniff",
                "X-Cache": "HIT"
            }
        )
    
    # Get user data (owner of the sheet)
    user_data = await db.users.find_one({"id": sheet["user_id"]}, {"_id": 0})
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario propietario no encontrado")
    
    # Get driver name if not titular
    driver_name = "Titular"
    if sheet.get("conductor_driver_id"):
        driver = await db.drivers.find_one(
            {"id": sheet["conductor_driver_id"], "user_id": sheet["user_id"]},
            {"_id": 0}
        )
        if driver:
            driver_name = driver["full_name"]
    
    # Generate PDF
    from pdf_generator import generate_route_sheet_pdf
    pdf_buffer = await asyncio.to_thread(generate_route_sheet_pdf, sheet, user_data, config, driver_name)
    pdf_bytes = pdf_buffer.getvalue()
    
    # Cache the PDF
    await cache_pdf(sheet_id, config_version, sheet_status, pdf_bytes)
    
    sheet_number = f"{sheet['seq_number']:03d}_{sheet['year']}"
    filename = f"hoja_ruta_{sheet_number}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"",
            "Cache-Control": "private, max-age=86400",
            "X-Content-Type-Options": "nosniff",
            "X-Cache": "MISS"
        }
    )


@admin_router.get("/route-sheets", response_model=List[dict])
async def admin_get_route_sheets(
    user_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    status: Optional[str] = None,
    user_visible: Optional[bool] = None,
    limit: int = 50,
    cursor: Optional[str] = None,
    admin: dict = Depends(get_current_admin)
):
    """Get all route sheets (admin) with pagination - can see ALL including hidden"""
    try:
        query = {}
        
        if user_id:
            query["user_id"] = user_id
        if status:
            query["status"] = status
        if user_visible is not None:
            query["user_visible"] = user_visible
        
        # Date filtering using pickup_datetime (same as user endpoints)
        # Convert Europe/Madrid local dates to UTC datetime
        madrid_tz = pytz.timezone("Europe/Madrid")
        
        if from_date or to_date:
            date_query = {}
            
            if from_date:
                try:
                    from_dt_local = madrid_tz.localize(
                        datetime.strptime(from_date, "%Y-%m-%d").replace(hour=0, minute=0, second=0)
                    )
                    from_dt_utc = from_dt_local.astimezone(pytz.UTC)
                    date_query["$gte"] = from_dt_utc
                except ValueError:
                    pass
            
            if to_date:
                try:
                    to_dt_local = madrid_tz.localize(
                        datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999)
                    )
                    to_dt_utc = to_dt_local.astimezone(pytz.UTC)
                    date_query["$lte"] = to_dt_utc
                except ValueError:
                    pass
            
            if date_query:
                query["pickup_datetime"] = date_query

        # Cursor pagination (stable by _id)
        if cursor:
            try:
                query["_id"] = {"$lt": ObjectId(cursor)}
            except Exception:
                pass
        
        # Sort by year and seq_number for consistent ordering
        sheets = await db.route_sheets.find(query).sort([("year", -1), ("seq_number", -1), ("_id", -1)]).limit(limit).to_list(limit)

        # Compute next cursor and collect user ids
        next_cursor = None
        user_ids = []
        for sheet in sheets:
            oid = sheet.pop("_id", None)
            if oid is not None:
                next_cursor = str(oid)
            # Safe sheet_number calculation
            seq = sheet.get('seq_number', 0) or 0
            year = sheet.get('year', 0) or 0
            sheet["sheet_number"] = f"{seq:03d}/{year}" if year else "---"
            user_ids.append(sheet.get("user_id"))
            
            # Convert datetime objects to ISO strings for JSON serialization
            for key in ['created_at', 'updated_at', 'pickup_datetime', 'prebooked_date', 'annulled_at']:
                if key in sheet and sheet[key] is not None:
                    if hasattr(sheet[key], 'isoformat'):
                        sheet[key] = sheet[key].isoformat()

        # Batch user lookup (avoid N+1)
        users_map = {}
        unique_user_ids = [uid for uid in set(user_ids) if uid]
        if unique_user_ids:
            users = await db.users.find(
                {"id": {"$in": unique_user_ids}},
                {"_id": 0, "id": 1, "email": 1, "full_name": 1}
            ).to_list(len(unique_user_ids))
            users_map = {u["id"]: u for u in users}
        
        # Attach user info
        for sheet in sheets:
            u = users_map.get(sheet.get("user_id"))
            if u:
                sheet["user_email"] = u.get("email")
                sheet["user_name"] = u.get("full_name")

        headers = {}
        if len(sheets) == limit and next_cursor:
            headers["X-Next-Cursor"] = next_cursor

        return JSONResponse(content=sheets, headers=headers)
    except Exception as e:
        logger.error(f"Error in admin_get_route_sheets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@admin_router.get("/config", response_model=dict)
async def admin_get_config(admin: dict = Depends(get_current_admin)):
    """Get app configuration"""
    config = await db.app_config.find_one({"id": "global"}, {"_id": 0})
    if not config:
        config = AppConfig().model_dump()
    return config


@admin_router.put("/config", response_model=dict)
async def admin_update_config(
    data: AppConfigUpdate,
    admin: dict = Depends(get_current_admin)
):
    """Update app configuration with validation"""
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    # Validate retention months
    if "hide_after_months" in update_data or "purge_after_months" in update_data:
        # Get current values
        current = await db.app_config.find_one({"id": "global"}, {"_id": 0})
        hide_months = update_data.get("hide_after_months", current.get("hide_after_months", 14) if current else 14)
        purge_months = update_data.get("purge_after_months", current.get("purge_after_months", 24) if current else 24)
        
        if purge_months <= hide_months:
            raise HTTPException(
                status_code=400,
                detail=f"purge_after_months ({purge_months}) debe ser mayor que hide_after_months ({hide_months})"
            )
        
        if hide_months < 1 or purge_months < 1:
            raise HTTPException(
                status_code=400,
                detail="Los meses de retención deben ser al menos 1"
            )
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc)
        
        # Check if PDF-affecting fields changed -> increment pdf_config_version
        pdf_fields = {"header_title", "header_line1", "header_line2", "legend_text"}
        if any(field in update_data for field in pdf_fields):
            # Increment pdf_config_version atomically
            await db.app_config.update_one(
                {"id": "global"},
                {
                    "$set": update_data,
                    "$inc": {"pdf_config_version": 1}
                },
                upsert=True
            )
            logger.info("PDF config changed - incremented pdf_config_version")
        else:
            await db.app_config.update_one(
                {"id": "global"},
                {"$set": update_data},
                upsert=True
            )
    
    return {"message": "Configuración actualizada"}


@admin_router.post("/run-retention")
async def admin_run_retention(
    dry_run: bool = Query(default=True, description="Preview sin hacer cambios"),
    admin: dict = Depends(get_current_admin)
):
    """
    Execute retention job manually (admin only).
    - Hides sheets older than hide_after_months
    - Purges sheets older than purge_after_months
    
    Use dry_run=true (default) to preview without changes.
    """
    import time
    start_time = time.time()
    now = datetime.now(timezone.utc)
    
    # Count before
    total_before = await db.route_sheets.count_documents({})
    visible_before = await db.route_sheets.count_documents({"user_visible": True})
    
    # Get sheets that would be affected
    hide_query = {"hide_at": {"$lte": now}, "user_visible": True}
    purge_query = {"purge_at": {"$lte": now}}
    
    to_hide = await db.route_sheets.count_documents(hide_query)
    to_purge = await db.route_sheets.count_documents(purge_query)
    
    result = {
        "dry_run": dry_run,
        "executed_at": now.isoformat(),
        "stats_before": {
            "total": total_before,
            "visible": visible_before,
            "hidden": total_before - visible_before
        },
        "to_hide": to_hide,
        "to_purge": to_purge,
        "message": ""
    }
    
    if dry_run:
        result["message"] = f"DRY RUN: Se ocultarían {to_hide} hojas y se eliminarían {to_purge}"
    else:
        try:
            hidden_count = 0
            purged_count = 0
            
            # Execute HIDE
            if to_hide > 0:
                hide_result = await db.route_sheets.update_many(
                    hide_query,
                    {"$set": {"user_visible": False}}
                )
                hidden_count = hide_result.modified_count
            
            # Execute PURGE
            if to_purge > 0:
                purge_result = await db.route_sheets.delete_many(purge_query)
                purged_count = purge_result.deleted_count
            
            # Count after
            total_after = await db.route_sheets.count_documents({})
            visible_after = await db.route_sheets.count_documents({"user_visible": True})
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log to retention_runs collection
            run_log = {
                "run_at": now,
                "hidden_count": hidden_count,
                "purged_count": purged_count,
                "dry_run": False,
                "trigger": "admin_manual",
                "duration_ms": duration_ms,
                "stats_before": {
                    "total": total_before,
                    "visible": visible_before
                },
                "stats_after": {
                    "total": total_after,
                    "visible": visible_after
                }
            }
            await db.retention_runs.insert_one(run_log)
            
            result["stats_after"] = {
                "total": total_after,
                "visible": visible_after,
                "hidden": total_after - visible_after
            }
            result["hidden"] = hidden_count
            result["purged"] = purged_count
            result["duration_ms"] = duration_ms
            result["message"] = f"Ejecutado: {hidden_count} hojas ocultas, {purged_count} hojas eliminadas"
            
            logger.info(f"Retention job executed by admin: {result['message']}")
        except Exception as e:
            logger.error(f"Retention job failed: {e}")
            raise HTTPException(status_code=500, detail=f"Error ejecutando retention: {str(e)}")
    
    return result


# ============== INTERNAL ENDPOINTS (for automated jobs) ==============

async def verify_job_token(x_job_token: Optional[str] = Header(None)) -> str:
    """Validate job token for internal endpoints"""
    if not RETENTION_JOB_TOKEN:
        logger.error("RETENTION_JOB_TOKEN not configured - internal endpoints disabled")
        raise HTTPException(status_code=503, detail="Job token not configured")
    
    if not x_job_token:
        raise HTTPException(status_code=401, detail="X-Job-Token header required")
    
    if x_job_token != RETENTION_JOB_TOKEN:
        logger.warning(f"Invalid job token attempt")
        raise HTTPException(status_code=403, detail="Invalid job token")
    
    return x_job_token


@internal_router.post("/run-retention")
async def internal_run_retention(token: str = Depends(verify_job_token)):
    """
    Execute retention job (for automated schedulers).
    
    Authentication: X-Job-Token header with RETENTION_JOB_TOKEN value.
    Always executes real retention (no dry_run).
    Uses atomic lock to prevent concurrent executions.
    
    Returns:
        - hidden_count: sheets hidden this run
        - purged_count: sheets purged this run  
        - duration_ms: execution time
        - run_at: ISO timestamp
    """
    import time
    start_time = time.time()
    now = datetime.now(timezone.utc)
    lock_expiry = now + timedelta(minutes=5)  # Lock expires after 5 min max
    
    # Acquire lock atomically
    lock_result = await db.retention_locks.find_one_and_update(
        {
            "_id": "retention_job",
            "$or": [
                {"locked": False},
                {"expires_at": {"$lt": now}}  # Expired lock
            ]
        },
        {
            "$set": {
                "locked": True,
                "acquired_at": now,
                "expires_at": lock_expiry
            }
        },
        return_document=ReturnDocument.AFTER,
        upsert=True
    )
    
    if not lock_result or not lock_result.get("locked"):
        raise HTTPException(
            status_code=409, 
            detail="Retention job already running. Try again later."
        )
    
    try:
        # Count before
        total_before = await db.route_sheets.count_documents({})
        visible_before = await db.route_sheets.count_documents({"user_visible": True})
        
        # Get sheets that will be affected
        hide_query = {"hide_at": {"$lte": now}, "user_visible": True}
        purge_query = {"purge_at": {"$lte": now}}
        
        to_hide = await db.route_sheets.count_documents(hide_query)
        to_purge = await db.route_sheets.count_documents(purge_query)
        
        hidden_count = 0
        purged_count = 0
        
        # Execute HIDE
        if to_hide > 0:
            hide_result = await db.route_sheets.update_many(
                hide_query,
                {"$set": {"user_visible": False}}
            )
            hidden_count = hide_result.modified_count
        
        # Execute PURGE (backup to TTL index)
        if to_purge > 0:
            # Log sheets being purged (without sensitive data)
            sheets = await db.route_sheets.find(
                purge_query,
                {"_id": 0, "id": 1, "user_id": 1, "year": 1, "seq_number": 1}
            ).to_list(100)
            
            for s in sheets:
                logger.info(f"Purging sheet: {s['seq_number']:03d}/{s['year']} (user: {s['user_id'][:8]}...)")
            
            purge_result = await db.route_sheets.delete_many(purge_query)
            purged_count = purge_result.deleted_count
        
        # Count after
        total_after = await db.route_sheets.count_documents({})
        visible_after = await db.route_sheets.count_documents({"user_visible": True})
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Log to retention_runs collection
        run_log = {
            "run_at": now,
            "hidden_count": hidden_count,
            "purged_count": purged_count,
            "dry_run": False,
            "trigger": "internal",
            "duration_ms": duration_ms,
            "stats_before": {
                "total": total_before,
                "visible": visible_before
            },
            "stats_after": {
                "total": total_after,
                "visible": visible_after
            }
        }
        await db.retention_runs.insert_one(run_log)
        
        logger.info(f"Internal retention job completed: hidden={hidden_count}, purged={purged_count}, duration={duration_ms}ms")
        
        return {
            "hidden_count": hidden_count,
            "purged_count": purged_count,
            "duration_ms": duration_ms,
            "run_at": now.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Internal retention job failed: {e}")
        raise HTTPException(status_code=500, detail=f"Retention job failed: {str(e)}")
    finally:
        # Release lock
        await db.retention_locks.update_one(
            {"_id": "retention_job"},
            {"$set": {"locked": False}}
        )


@admin_router.get("/retention-runs")
async def admin_get_retention_runs(
    limit: int = Query(default=10, le=50),
    admin: dict = Depends(get_current_admin)
):
    """Get recent retention job executions"""
    runs = await db.retention_runs.find(
        {},
        {"_id": 0}
    ).sort("run_at", -1).limit(limit).to_list(limit)
    
    # Convert datetime to ISO string for JSON
    for run in runs:
        if isinstance(run.get("run_at"), datetime):
            run["run_at"] = run["run_at"].isoformat()
    
    return runs


@admin_router.get("/retention-runs/last")
async def admin_get_last_retention_run(admin: dict = Depends(get_current_admin)):
    """
    Get the most recent retention job execution with status indicator.
    
    Status:
    - OK: last run < 36 hours ago
    - WARN: last run 36-72 hours ago
    - CRIT: last run > 72 hours ago OR never executed
    """
    run = await db.retention_runs.find_one(
        {},
        {"_id": 0},
        sort=[("run_at", -1)]
    )
    
    now = datetime.now(timezone.utc)
    
    if not run:
        return {
            "last_run_at": None,
            "hours_since_last_run": None,
            "status": "CRIT",
            "status_message": "Nunca se ha ejecutado",
            "trigger": None,
            "hidden_count": None,
            "purged_count": None,
            "duration_ms": None
        }
    
    # Calculate hours since last run
    run_at = run.get("run_at")
    if isinstance(run_at, datetime):
        if run_at.tzinfo is None:
            run_at = run_at.replace(tzinfo=timezone.utc)
        hours_since = (now - run_at).total_seconds() / 3600
    else:
        hours_since = None
    
    # Determine status
    if hours_since is None:
        status = "CRIT"
        status_message = "Fecha de ejecución inválida"
    elif hours_since > 72:
        status = "CRIT"
        status_message = f"Última ejecución hace {int(hours_since)} horas (>72h)"
    elif hours_since > 36:
        status = "WARN"
        status_message = f"Última ejecución hace {int(hours_since)} horas (>36h)"
    else:
        status = "OK"
        status_message = f"Última ejecución hace {int(hours_since)} horas"
    
    return {
        "last_run_at": run_at.isoformat() if isinstance(run_at, datetime) else run_at,
        "hours_since_last_run": round(hours_since, 1) if hours_since else None,
        "status": status,
        "status_message": status_message,
        "trigger": run.get("trigger"),
        "hidden_count": run.get("hidden_count"),
        "purged_count": run.get("purged_count"),
        "duration_ms": run.get("duration_ms")
    }


@admin_router.get("/debug/db-info")
async def admin_debug_db_info(admin: dict = Depends(get_current_admin)):
    """
    Debug endpoint: DB info for troubleshooting admin/web discrepancies.
    Returns environment, database name, counts, and latest records.
    """
    # Get counts
    users_count = await db.users.count_documents({})
    sheets_count = await db.route_sheets.count_documents({})
    
    # Get latest user
    last_user = await db.users.find_one(
        {},
        {"_id": 0, "email": 1, "created_at": 1},
        sort=[("created_at", -1)]
    )
    
    # Get latest sheet
    last_sheet = await db.route_sheets.find_one(
        {},
        {"_id": 0, "sheet_number": 1, "created_at": 1},
        sort=[("created_at", -1)]
    )
    
    return {
        "app_env": os.environ.get("ENVIRONMENT", "development"),
        "db_name": db.name,
        "users_count": users_count,
        "sheets_count": sheets_count,
        "last_user_created_at": last_user.get("created_at").isoformat() if last_user and last_user.get("created_at") else None,
        "last_user_email": last_user.get("email") if last_user else None,
        "last_sheet_created_at": last_sheet.get("created_at").isoformat() if last_sheet and last_sheet.get("created_at") else None,
        "last_sheet_number": last_sheet.get("sheet_number") if last_sheet else None
    }


# Include routers
api_router.include_router(auth_router)
api_router.include_router(mobile_auth_router)
api_router.include_router(user_router)
api_router.include_router(sheets_router)
api_router.include_router(admin_router)
api_router.include_router(internal_router)
app.include_router(api_router)


# CORS - Sanitized origins, fail-closed in production
def get_cors_origins() -> list:
    """Parse and sanitize CORS origins from environment"""
    raw = os.environ.get("CORS_ORIGINS", "")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins


cors_origins = get_cors_origins()

# Fail closed in production if no origins configured
if IS_PRODUCTION and not cors_origins:
    logger.error("CORS_ORIGINS not configured in production - this is a security risk")
    raise RuntimeError("CORS_ORIGINS must be configured in production")

if not cors_origins:
    logger.warning("CORS_ORIGINS not set - defaulting to localhost for development")
    cors_origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins,  # Explicit list, no wildcards with credentials
    allow_methods=["*"],
    allow_headers=["*"],
)
