"""
RutasFast - MongoDB Models
Colecciones: users, drivers, route_sheets, app_config, password_reset_tokens

Pydantic v2 with strict validation:
- extra="forbid" on all request models
- String normalization (strip, empty->None)
- Field-specific validation (dni upper, vehicle_plate upper)
"""
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator, model_validator
from typing import Optional, List, Literal, Any
from datetime import datetime, timezone
import uuid


def generate_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ============== VALIDATORS HELPERS ==============
def normalize_string(v: Any) -> Optional[str]:
    """Strip string, return None if empty"""
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        return v if v else None
    return v


def normalize_upper(v: Any) -> Optional[str]:
    """Strip and uppercase string, return None if empty"""
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip().upper()
        return v if v else None
    return v


def require_non_empty(v: str, field_name: str) -> str:
    """Validate required string is not empty after strip"""
    if not v or not v.strip():
        raise ValueError(f'{field_name} no puede estar vacío')
    return v.strip()


# ============== DRIVER MODELS ==============
class DriverCreate(BaseModel):
    """Create a new driver - extra fields forbidden"""
    model_config = ConfigDict(extra="forbid")
    
    full_name: str
    dni: str
    
    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v):
        v = v.strip() if v else ''
        if not v:
            raise ValueError('full_name no puede estar vacío')
        return v
    
    @field_validator('dni')
    @classmethod
    def validate_dni(cls, v):
        v = v.strip().upper() if v else ''
        if not v:
            raise ValueError('dni no puede estar vacío')
        return v


class DriverUpdate(BaseModel):
    """Update a driver - all fields optional, extra forbidden"""
    model_config = ConfigDict(extra="forbid")
    
    full_name: Optional[str] = None
    dni: Optional[str] = None
    
    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v):
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError('full_name no puede estar vacío si se proporciona')
        return v
    
    @field_validator('dni')
    @classmethod
    def validate_dni(cls, v):
        if v is None:
            return None
        v = v.strip().upper()
        if not v:
            raise ValueError('dni no puede estar vacío si se proporciona')
        return v
    
    @model_validator(mode='after')
    def check_at_least_one_field(self):
        if self.full_name is None and self.dni is None:
            raise ValueError('No hay campos para actualizar')
        return self


class Driver(BaseModel):
    """Driver stored in DB"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    user_id: str
    full_name: str
    dni: str
    created_at: datetime = Field(default_factory=utc_now)


# ============== USER MODELS ==============
class UserCreate(BaseModel):
    """Create a new user - extra fields forbidden"""
    model_config = ConfigDict(extra="forbid")
    
    full_name: str
    dni_cif: str
    license_number: str
    license_council: str
    phone: str
    email: EmailStr
    password: str = Field(max_length=128)
    vehicle_brand: str
    vehicle_model: str
    vehicle_plate: str
    vehicle_license_number: Optional[str] = None  # Nº licencia/permiso del vehículo
    drivers: Optional[List[DriverCreate]] = []
    
    @field_validator('full_name', 'license_number', 'license_council', 'phone', 'vehicle_brand', 'vehicle_model')
    @classmethod
    def validate_required_strings(cls, v, info):
        if not v or not v.strip():
            raise ValueError(f'{info.field_name} no puede estar vacío')
        return v.strip()
    
    @field_validator('dni_cif')
    @classmethod
    def validate_dni_cif(cls, v):
        if not v or not v.strip():
            raise ValueError('dni_cif no puede estar vacío')
        return v.strip().upper()
    
    @field_validator('vehicle_plate')
    @classmethod
    def validate_vehicle_plate(cls, v):
        if not v or not v.strip():
            raise ValueError('vehicle_plate no puede estar vacío')
        return v.strip().upper()
    
    @field_validator('vehicle_license_number')
    @classmethod
    def validate_vehicle_license_number(cls, v):
        if v is None:
            return None
        v = v.strip()
        return v if v else None
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not v:
            raise ValueError('password no puede estar vacío')
        if len(v) < 8:
            raise ValueError('password debe tener al menos 8 caracteres')
        return v


class UserUpdate(BaseModel):
    """Update user profile - extra fields forbidden (no email, password, status, etc.)"""
    model_config = ConfigDict(extra="forbid")
    
    full_name: Optional[str] = None
    dni_cif: Optional[str] = None
    license_number: Optional[str] = None
    license_council: Optional[str] = None
    phone: Optional[str] = None
    vehicle_brand: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_plate: Optional[str] = None
    vehicle_license_number: Optional[str] = None  # Nº licencia/permiso del vehículo
    
    @field_validator('full_name', 'license_number', 'license_council', 'phone', 'vehicle_brand', 'vehicle_model', 'vehicle_license_number')
    @classmethod
    def validate_optional_strings(cls, v, info):
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None  # Permitir string vacío como None
        return v
    
    @field_validator('dni_cif')
    @classmethod
    def validate_dni_cif(cls, v):
        if v is None:
            return None
        v = v.strip().upper()
        if not v:
            raise ValueError('dni_cif no puede estar vacío si se proporciona')
        return v
    
    @field_validator('vehicle_plate')
    @classmethod
    def validate_vehicle_plate(cls, v):
        if v is None:
            return None
        v = v.strip().upper()
        if not v:
            raise ValueError('vehicle_plate no puede estar vacío si se proporciona')
        return v


class User(BaseModel):
    """User stored in DB"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    full_name: str
    dni_cif: str
    license_number: str
    license_council: str
    phone: str
    email: str
    password_hash: str
    vehicle_brand: str
    vehicle_model: str
    vehicle_plate: str
    status: Literal["PENDING", "APPROVED"] = "PENDING"
    token_version: int = 0
    must_change_password: bool = False
    temp_password_expires_at: Optional[datetime] = None
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
    email: str
    vehicle_brand: str
    vehicle_model: str
    vehicle_plate: str
    vehicle_license_number: Optional[str] = None
    status: str
    must_change_password: bool = False
    created_at: datetime
    updated_at: datetime


# ============== PASSWORD CHANGE MODELS ==============
class ChangePasswordRequest(BaseModel):
    """Change password request - extra fields forbidden"""
    model_config = ConfigDict(extra="forbid")
    
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)
    
    @field_validator('current_password')
    @classmethod
    def validate_current_password(cls, v):
        if not v:
            raise ValueError('current_password no puede estar vacío')
        return v
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if not v or len(v) < 8:
            raise ValueError('new_password debe tener al menos 8 caracteres')
        return v


# ============== ROUTE SHEET MODELS ==============
class RouteSheetCreate(BaseModel):
    """Create a new route sheet - extra fields forbidden"""
    model_config = ConfigDict(extra="forbid")
    
    conductor_driver_id: Optional[str] = None
    contractor_phone: Optional[str] = None
    contractor_email: Optional[EmailStr] = None
    prebooked_date: str
    prebooked_locality: str
    pickup_type: Literal["AIRPORT", "OTHER"]
    flight_number: Optional[str] = None
    pickup_address: Optional[str] = None
    pickup_datetime: str
    destination: str
    passenger_info: str  # Obligatorio: datos de la persona o personas a recoger
    
    @field_validator('conductor_driver_id', 'contractor_phone', 'flight_number', 'pickup_address')
    @classmethod
    def normalize_optional_strings(cls, v):
        if v is None:
            return None
        v = v.strip()
        return v if v else None
    
    @field_validator('prebooked_date', 'prebooked_locality', 'pickup_datetime', 'destination', 'passenger_info')
    @classmethod
    def validate_required_strings(cls, v, info):
        if not v or not v.strip():
            raise ValueError(f'{info.field_name} no puede estar vacío')
        return v.strip()


class RouteSheet(BaseModel):
    """Route sheet stored in DB"""
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
    passenger_info: Optional[str] = None  # Datos de pasajeros (obligatorio en nuevas hojas)
    status: Literal["ACTIVE", "ANNULLED"] = "ACTIVE"
    annulled_at: Optional[datetime] = None
    annul_reason: Optional[str] = None
    user_visible: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    hide_at: Optional[datetime] = None
    purge_at: Optional[datetime] = None


class RouteSheetAnnul(BaseModel):
    """Annul a route sheet - extra fields forbidden"""
    model_config = ConfigDict(extra="forbid")
    
    reason: Optional[str] = Field(default=None, max_length=500)
    
    @field_validator('reason')
    @classmethod
    def normalize_reason(cls, v):
        if v is None:
            return None
        v = v.strip()
        return v if v else None


# ============== APP CONFIG MODEL ==============
class AppConfig(BaseModel):
    """App configuration stored in DB"""
    model_config = ConfigDict(extra="ignore")
    id: str = "global"
    header_title: str = "HOJA DE RUTA"
    header_line1: str = "CONSEJERIA DE MOVILIDAD, MEDIO AMBIENTE Y GESTION DE EMERGENCIAS"
    header_line2: str = "Servicio de Inspección de Transportes"
    legend_text: str = "Es obligatorio conservar los registros durante 12 meses desde la fecha de recogida del servicio."
    hide_after_months: int = 14
    purge_after_months: int = 24
    pdf_config_version: int = 1
    updated_at: datetime = Field(default_factory=utc_now)


class AppConfigUpdate(BaseModel):
    """Update app configuration - extra fields forbidden"""
    model_config = ConfigDict(extra="forbid")
    
    header_title: Optional[str] = None
    header_line1: Optional[str] = None
    header_line2: Optional[str] = None
    legend_text: Optional[str] = None
    hide_after_months: Optional[int] = Field(default=None, ge=1, le=36)
    purge_after_months: Optional[int] = Field(default=None, ge=2, le=60)
    
    @field_validator('header_title', 'header_line1', 'header_line2', 'legend_text')
    @classmethod
    def normalize_optional_strings(cls, v):
        if v is None:
            return None
        v = v.strip()
        return v if v else None
    
    @model_validator(mode='after')
    def validate_retention_months(self):
        # Only validate if both are provided in the same request
        if self.hide_after_months is not None and self.purge_after_months is not None:
            if self.purge_after_months <= self.hide_after_months:
                raise ValueError('purge_after_months debe ser mayor que hide_after_months')
        return self


# ============== AUTH MODELS ==============
class LoginRequest(BaseModel):
    """Login request - extra fields forbidden"""
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str
    new_password: str


class PasswordResetToken(BaseModel):
    """Password reset token stored in DB"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    user_id: str
    token_hash: str
    expires_at: datetime
    used: bool = False
    created_at: datetime = Field(default_factory=utc_now)


# ============== ADMIN MODELS ==============
class AdminLoginRequest(BaseModel):
    """Admin login request - extra fields forbidden"""
    model_config = ConfigDict(extra="forbid")
    username: str
    password: str
