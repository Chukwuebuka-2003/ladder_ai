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
    """
    Hash a plaintext password using bcrypt and return the resulting hash.
    
    Returns:
        A bcrypt-formatted hash string suitable for storing in a user database.
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create and return a signed JWT access token for the given payload.
    
    The function copies `data` to build the token payload, sets the `exp` (expiration) and `iat` (issued-at) claims, and signs the token with the module private key using the ES256 algorithm. If `expires_delta` is provided it controls the token lifetime; otherwise the module default (ACCESS_TOKEN_EXPIRE_MINUTES) is used. If a `sub` claim is present as an int, it will be converted to a string.
    
    Parameters:
        data (dict): Claims to include in the token payload.
        expires_delta (Optional[timedelta]): Optional time delta to use for the `exp` claim (overrides default).
    
    Returns:
        str: The encoded JWT as a string.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    # Ensure 'sub' claim is a string if it exists
    if "sub" in to_encode and isinstance(to_encode["sub"], int):
        to_encode["sub"] = str(to_encode["sub"])

    encoded_jwt = jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str) -> dict:
    """
    Verify a JWT access token and return its decoded payload.
    
    Decodes `token` using the module public key and the ES256 algorithm. On success returns the token payload as a dict; returns None if the token is invalid, expired, or any JWT decoding error occurs.
    """
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        # If any JWT-related error occurs (e.g., expired, invalid signature), return None.
        return None
