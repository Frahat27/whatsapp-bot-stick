"""
Admin panel authentication — JWT login.

Solo 2 usuarios: Franco y Cynthia.
Credenciales: username + password (bcrypt hash en .env).
Token JWT expira en 24h.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from src.config import get_settings
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin_name: str
    admin_phone: str


class AdminUser(BaseModel):
    username: str
    name: str
    phone: str


def _get_admin_registry() -> dict:
    """
    Construye el registro de admins desde config.
    Returns: {username: {name, phone, password_hash}}
    """
    settings = get_settings()
    phones = settings.admin_phone_list
    names = settings.admin_name_list
    hashes = [
        settings.admin_password_hash_franco,
        settings.admin_password_hash_cynthia,
    ]
    registry = {}
    for name, phone, pw_hash in zip(names, phones, hashes):
        if pw_hash:  # Solo registrar admins con password configurado
            username = name.lower()
            registry[username] = {
                "name": name,
                "phone": phone,
                "password_hash": pw_hash,
            }
    return registry


@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    """Login con username/password. Retorna JWT."""
    registry = _get_admin_registry()
    user = registry.get(form.username.lower())
    if not user or not pwd_context.verify(form.password, user["password_hash"]):
        logger.warning("admin_login_failed", username=form.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()
    expire = datetime.utcnow() + timedelta(hours=settings.jwt_access_token_expire_hours)
    token = jwt.encode(
        {"sub": form.username.lower(), "exp": expire},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    logger.info("admin_login_success", username=form.username)
    return TokenResponse(
        access_token=token,
        admin_name=user["name"],
        admin_phone=user["phone"],
    )


async def get_current_admin(token: str = Depends(oauth2_scheme)) -> AdminUser:
    """FastAPI dependency: valida JWT y retorna el admin autenticado."""
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    registry = _get_admin_registry()
    user = registry.get(username)
    if not user:
        raise credentials_exception

    return AdminUser(username=username, name=user["name"], phone=user["phone"])


def hash_password(plain: str) -> str:
    """Utility: genera bcrypt hash. Usar desde consola para crear passwords."""
    return pwd_context.hash(plain)
