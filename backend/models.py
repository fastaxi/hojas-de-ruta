"""
RutasFast - MongoDB Models
Colecciones: users, drivers, route_sheets, app_config, password_reset_tokens
"""
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime, timezone
import uuid


def generate_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ============== USER MODELS ==============
class DriverBase(BaseModel):
    full_name: str
    dni: str


class DriverCreate(DriverBase):
    pass


class Driver(DriverBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    user_id: str
    created_at: datetime = Field(default_factory=utc_now)


class UserBase(BaseModel):
    full_name: str
    dni_cif: str
    license_number: str
    license_council: str
    phone: str
    email: EmailStr
    vehicle_brand: str
    vehicle_model: str
    vehicle_plate: str


class UserCreate(UserBase):
    password: str
    drivers: Optional[List[DriverCreate]] = []


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    dni_cif: Optional[str] = None
    license_number: Optional[str] = None
    license_council: Optional[str] = None
    phone: Optional[str] = None
    vehicle_brand: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_plate: Optional[str] = None


class User(UserBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    password_hash: str
    status: Literal["PENDING", "APPROVED"] = "PENDING"
    token_version: int = 0  # For session invalidation
    must_change_password: bool = False  # Force password change on next login
    temp_password_expires_at: Optional[datetime] = None  # Temp password expiry (72h)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class UserPublic(BaseModel):
    """User data without sensitive fields"""
    model_config = ConfigDict(extra="ignore")
    id: str
    full_name: str
    dni_cif: str
    license_number: str
    license_council: str
    phone: str
    email: EmailStr
    vehicle_brand: str
    vehicle_model: str
    vehicle_plate: str
    status: str
    must_change_password: bool = False
    created_at: datetime
    updated_at: datetime


# ============== PASSWORD CHANGE MODELS ==============
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ============== ROUTE SHEET MODELS ==============
class RouteSheetCreate(BaseModel):
    conductor_driver_id: Optional[str] = None  # null = titular
    contractor_phone: Optional[str] = None
    contractor_email: Optional[EmailStr] = None
    prebooked_date: str  # ISO date string
    prebooked_locality: str
    pickup_type: Literal["AIRPORT", "OTHER"]
    flight_number: Optional[str] = None
    pickup_address: Optional[str] = None
    pickup_datetime: str  # ISO datetime string
    destination: str


class RouteSheet(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    user_id: str
    year: int
    seq_number: int
    conductor_driver_id: Optional[str] = None
    contractor_phone: Optional[str] = None
    contractor_email: Optional[str] = None
    prebooked_date: str
    prebooked_locality: str
    pickup_type: Literal["AIRPORT", "OTHER"]
    flight_number: Optional[str] = None
    pickup_address: Optional[str] = None
    pickup_datetime: str
    destination: str
    status: Literal["ACTIVE", "ANNULLED"] = "ACTIVE"
    annulled_at: Optional[datetime] = None
    annul_reason: Optional[str] = None
    user_visible: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    hide_at: Optional[datetime] = None  # created_at + 14 meses
    purge_at: Optional[datetime] = None  # created_at + 24 meses


class RouteSheetAnnul(BaseModel):
    reason: Optional[str] = None


# ============== APP CONFIG MODEL ==============
class AppConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = "global"
    header_title: str = "HOJA DE RUTA"
    header_line1: str = "CONSEJERIA DE MOVILIDAD, MEDIO AMBIENTE Y GESTION DE EMERGENCIAS"
    header_line2: str = "Servicio de Inspección de Transportes"
    legend_text: str = "Es obligatorio conservar los registros durante 12 meses desde la fecha de recogida del servicio."
    hide_after_months: int = 14
    purge_after_months: int = 24
    updated_at: datetime = Field(default_factory=utc_now)


class AppConfigUpdate(BaseModel):
    header_title: Optional[str] = None
    header_line1: Optional[str] = None
    header_line2: Optional[str] = None
    legend_text: Optional[str] = None
    hide_after_months: Optional[int] = None
    purge_after_months: Optional[int] = None


# ============== AUTH MODELS ==============
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class PasswordResetToken(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    user_id: str
    token_hash: str  # Hasheado, no en claro
    expires_at: datetime
    used: bool = False
    created_at: datetime = Field(default_factory=utc_now)


# ============== ADMIN MODELS ==============
class AdminLoginRequest(BaseModel):
    username: str
    password: str
