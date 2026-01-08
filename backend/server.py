"""
RutasFast - Main FastAPI Server
Backend for taxi route sheet management app
"""
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header, Query
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument
from bson import ObjectId
import os
import logging
import re
import pytz
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone, timedelta, date
import io

# Local imports
from models import (
    User, UserCreate, UserUpdate, UserPublic,
    Driver, DriverCreate,
    RouteSheet, RouteSheetCreate, RouteSheetAnnul,
    AppConfig, AppConfigUpdate,
    LoginRequest, TokenResponse, RefreshRequest,
    ForgotPasswordRequest, ResetPasswordRequest, PasswordResetToken,
    AdminLoginRequest
)
from auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    generate_reset_token, hash_reset_token, verify_reset_token_hash,
    verify_admin_password, create_admin_token
)
from email_service import (
    send_approval_email, send_password_reset_email, is_email_configured
)
from dateutil.relativedelta import relativedelta

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="RutasFast API", version="1.0.0")

# Create routers
api_router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/auth", tags=["auth"])
user_router = APIRouter(prefix="/me", tags=["user"])
sheets_router = APIRouter(prefix="/route-sheets", tags=["route-sheets"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============== STARTUP / SHUTDOWN ==============
@app.on_event("startup")
async def startup_db():
    """Initialize database indexes and default config"""
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.drivers.create_index("user_id")
    await db.drivers.create_index("id", unique=True)
    await db.route_sheets.create_index([("user_id", 1), ("created_at", -1)])
    # CRITICAL: Unique index for atomic numbering
    await db.route_sheets.create_index(
        [("user_id", 1), ("year", 1), ("seq_number", 1)], 
        unique=True
    )
    await db.route_sheets.create_index("status")
    await db.route_sheets.create_index("user_visible")
    await db.route_sheets.create_index("id", unique=True)
    # Index for purge TTL (requires BSON Date, not string)
    await db.route_sheets.create_index("purge_at", expireAfterSeconds=0)
    # Token hash unique + TTL on expires_at
    await db.password_reset_tokens.create_index("token_hash", unique=True)
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    # Counters collection for atomic seq_number
    await db.counters.create_index([("user_id", 1), ("year", 1)], unique=True)
    
    # Initialize app_config if not exists
    existing_config = await db.app_config.find_one({"id": "global"}, {"_id": 0})
    if not existing_config:
        config = AppConfig()
        await db.app_config.insert_one(config.model_dump())
        logger.info("Initialized default app_config")
    
    logger.info("Database indexes created")


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


@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "email_configured": is_email_configured()}


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


@auth_router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    """Login user - must be approved"""
    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    if user["status"] != "APPROVED":
        raise HTTPException(
            status_code=403,
            detail="Este usuario aun no ha sido verificado por el administrador."
        )
    
    access_token = create_access_token(user["id"], user["email"])
    refresh_token = create_refresh_token(user["id"])
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(data: RefreshRequest):
    """Refresh access token using refresh token"""
    payload = decode_token(data.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token inválido")
    
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    
    if user["status"] != "APPROVED":
        raise HTTPException(status_code=403, detail="Usuario no verificado")
    
    # Create new tokens (rotation)
    access_token = create_access_token(user["id"], user["email"])
    refresh_token = create_refresh_token(user["id"])
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@auth_router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest):
    """Request password reset email"""
    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    
    # Always return success to prevent email enumeration
    if not user:
        return {"message": "Si el email existe, recibirás un enlace de recuperación"}
    
    # Generate reset token (plain for email, hash for storage)
    token, token_hash = generate_reset_token()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=1)
    
    reset_token = PasswordResetToken(
        user_id=user["id"],
        token_hash=token_hash,
        expires_at=expires_at
    )
    
    # Keep expires_at as datetime for TTL index to work
    token_dict = reset_token.model_dump()
    # datetime fields stay as datetime (BSON Date)
    
    await db.password_reset_tokens.insert_one(token_dict)
    
    # Send email with plain token (user clicks link with token)
    await send_password_reset_email(user["email"], user["full_name"], token)
    
    return {"message": "Si el email existe, recibirás un enlace de recuperación"}


@auth_router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest):
    """Reset password using token (one-time use, atomic validation)"""
    token_hash = hash_reset_token(data.token)
    now = datetime.now(timezone.utc)
    
    # ATOMIC: Find valid token AND mark as used in single operation
    # Compare expires_at as datetime (BSON Date), not string
    token_doc = await db.password_reset_tokens.find_one_and_update(
        {
            "token_hash": token_hash,
            "used": False,
            "expires_at": {"$gt": now}  # datetime comparison
        },
        {
            "$set": {
                "used": True,
                "used_at": now  # datetime, not string
            }
        },
        return_document=ReturnDocument.BEFORE
    )
    
    if not token_doc:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")
    
    # Update password
    new_hash = hash_password(data.new_password)
    await db.users.update_one(
        {"id": token_doc["user_id"]},
        {"$set": {
            "password_hash": new_hash,
            "updated_at": now  # datetime
        }}
    )
    
    logger.info(f"Password reset for user {token_doc['user_id']}")
    return {"message": "Contraseña actualizada correctamente"}


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
    data: DriverCreate,
    user: dict = Depends(get_current_user)
):
    """Update a driver"""
    result = await db.drivers.update_one(
        {"id": driver_id, "user_id": user["id"]},
        {"$set": {"full_name": data.full_name, "dni": data.dni}}
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
    
    # 2. Flight number validation for airport pickup
    if data.pickup_type == "AIRPORT":
        if not data.flight_number:
            raise HTTPException(
                status_code=400,
                detail="Número de vuelo obligatorio para recogida en aeropuerto"
            )
        if not re.match(r'^[A-Z]{2}\d{3,4}$', data.flight_number):
            raise HTTPException(
                status_code=400,
                detail="Formato de vuelo inválido. Ejemplo: VY1234"
            )
    
    # 3. Pickup address required for non-airport
    if data.pickup_type == "OTHER":
        if not data.pickup_address or not data.pickup_address.strip():
            raise HTTPException(
                status_code=400,
                detail="Dirección de recogida obligatoria para recogida fuera del aeropuerto"
            )
    
    # ============== ATOMIC NUMBERING ==============
    current_year = datetime.now(timezone.utc).year
    
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
    
    sheet = RouteSheet(
        user_id=user["id"],
        year=current_year,
        seq_number=next_seq,
        hide_at=hide_at,
        purge_at=purge_at,
        **data.model_dump()
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
    
    # Query with stable sort: pickup_datetime desc, _id desc
    sheets = await db.route_sheets.find(
        query
    ).sort([("pickup_datetime", -1), ("_id", -1)]).limit(limit).to_list(limit)
    
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
    
    return {"message": "Hoja anulada correctamente"}


@sheets_router.get("/{sheet_id}/pdf")
async def get_route_sheet_pdf(sheet_id: str, user: dict = Depends(get_current_user)):
    """Generate PDF for a single route sheet (only if user_visible=true)"""
    sheet = await db.route_sheets.find_one(
        {"id": sheet_id, "user_id": user["id"], "user_visible": True},
        {"_id": 0}
    )
    if not sheet:
        raise HTTPException(status_code=404, detail="Hoja no encontrada")
    
    # Get config for PDF headers
    config = await db.app_config.find_one({"id": "global"}, {"_id": 0})
    if not config:
        config = AppConfig().model_dump()
    
    # Get user full data
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    
    # Get driver name if not titular
    driver_name = "Titular"
    if sheet.get("conductor_driver_id"):
        driver = await db.drivers.find_one(
            {"id": sheet["conductor_driver_id"]},
            {"_id": 0}
        )
        if driver:
            driver_name = driver["full_name"]
    
    # Generate PDF
    from pdf_generator import generate_route_sheet_pdf
    pdf_buffer = generate_route_sheet_pdf(sheet, user_data, config, driver_name)
    
    sheet_number = f"{sheet['seq_number']:03d}_{sheet['year']}"
    filename = f"hoja_ruta_{sheet_number}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@sheets_router.get("/pdf/range")
async def get_route_sheets_pdf_range(
    from_date: date,
    to_date: date,
    user: dict = Depends(get_current_user)
):
    """
    Generate PDF for multiple route sheets in date range.
    - Filters by pickup_datetime (Europe/Madrid to UTC)
    - Always user_visible=true
    - Never includes annulled sheets
    """
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
    ).sort("created_at", 1).to_list(1000)
    
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
    pdf_buffer = generate_multi_sheet_pdf(sheets, user_data, config, drivers_map)
    
    filename = f"hojas_ruta_{from_date}_a_{to_date}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============== ADMIN ENDPOINTS ==============
@admin_router.post("/login")
async def admin_login(data: AdminLoginRequest):
    """Admin login"""
    admin_username = os.environ.get("ADMIN_USERNAME", "admin")
    
    if data.username != admin_username:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    if not verify_admin_password(data.password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    token = create_admin_token()
    return {"access_token": token, "token_type": "bearer"}


@admin_router.get("/users", response_model=List[dict])
async def admin_get_users(
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    cursor: Optional[str] = None,
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
    
    # Cursor-based pagination using created_at
    if cursor:
        query["created_at"] = {"$lt": cursor}
    
    users = await db.users.find(
        query,
        {"_id": 0, "password_hash": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return users


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
    """Approve user registration"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if user["status"] == "APPROVED":
        raise HTTPException(status_code=400, detail="Usuario ya está aprobado")
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "status": "APPROVED",
            "updated_at": datetime.now(timezone.utc)  # datetime
        }}
    )
    
    # Send approval email
    email_result = await send_approval_email(user["email"], user["full_name"])
    
    logger.info(f"User approved: {user['email']}")
    
    return {
        "message": "Usuario aprobado",
        "email_sent": email_result["success"]
    }


@admin_router.post("/users/{user_id}/send-reset")
async def admin_send_reset(user_id: str, admin: dict = Depends(get_current_admin)):
    """Send password reset to user (admin)"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Generate reset token (plain for email, hash for storage)
    token, token_hash = generate_reset_token()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=1)
    
    reset_token = PasswordResetToken(
        user_id=user["id"],
        token_hash=token_hash,
        expires_at=expires_at
    )
    
    # Keep datetime as native for TTL
    token_dict = reset_token.model_dump()
    
    await db.password_reset_tokens.insert_one(token_dict)
    
    # Send email with plain token
    email_result = await send_password_reset_email(user["email"], user["full_name"], token)
    
    return {
        "message": "Email de recuperación enviado",
        "email_sent": email_result["success"]
    }


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
    query = {}
    
    if user_id:
        query["user_id"] = user_id
    if status:
        query["status"] = status
    if user_visible is not None:
        query["user_visible"] = user_visible
    if from_date:
        query["created_at"] = {"$gte": from_date}
    if to_date:
        if "created_at" in query:
            query["created_at"]["$lte"] = to_date
        else:
            query["created_at"] = {"$lte": to_date}
    
    # Cursor-based pagination
    if cursor:
        if "created_at" in query:
            query["created_at"]["$lt"] = cursor
        else:
            query["created_at"] = {"$lt": cursor}
    
    sheets = await db.route_sheets.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Add formatted sheet number and user info
    for sheet in sheets:
        sheet["sheet_number"] = f"{sheet['seq_number']:03d}/{sheet['year']}"
        user = await db.users.find_one({"id": sheet["user_id"]}, {"_id": 0, "email": 1, "full_name": 1})
        if user:
            sheet["user_email"] = user.get("email")
            sheet["user_name"] = user.get("full_name")
    
    return sheets


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
    """Update app configuration"""
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc)  # datetime
        await db.app_config.update_one(
            {"id": "global"},
            {"$set": update_data},
            upsert=True
        )
    
    return {"message": "Configuración actualizada"}


# Include routers
api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(sheets_router)
api_router.include_router(admin_router)
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
