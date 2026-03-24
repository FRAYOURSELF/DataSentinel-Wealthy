from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

# bcrypt has a hard 72-byte input limit; bcrypt_sha256 pre-hashes input to avoid
# truncation and backend-specific errors while retaining bcrypt as verifier for
# existing hashes.
pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, user_id: int) -> tuple[str, int]:
    expires_in = settings.jwt_expiry_minutes * 60
    expire_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    payload = {"sub": subject, "user_id": user_id, "exp": expire_at}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_in
