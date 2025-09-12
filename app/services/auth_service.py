import os
from datetime import datetime, timedelta
import jwt
from typing import Optional
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv()

ALGORITHM = "ES256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") # Use bcrypt for hashing

# ONLY read keys from environment variables
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
PUBLIC_KEY = os.getenv("PUBLIC_KEY")

# Validate that both keys are provided
if not PRIVATE_KEY:
    raise ValueError("PRIVATE_KEY is not set in .env file")

if not PUBLIC_KEY:
    raise ValueError("PUBLIC_KEY is not set in .env file")

# Password Hashing Functions
def get_password_hash(password: str) -> str:
    """Hashes the given password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    # Ensure 'sub' claim is a string if it exists
    if "sub" in to_encode and isinstance(to_encode["sub"], int):
        to_encode["sub"] = str(to_encode["sub"])

    encoded_jwt = jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str) -> dict:
    """Verifies the JWT access token and returns its payload."""
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        # If any JWT-related error occurs (e.g., expired, invalid signature), return None.
        return None
