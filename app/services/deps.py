from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session
from database import get_db
from models import User
from .auth_service import verify_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Resolve and return the currently authenticated User from an OAuth2 access token.
    
    Validates the provided access token using verify_access_token, extracts the user id from the token's "sub" claim, and loads the corresponding User from the database. Raises HTTP 401 Unauthorized if the token is invalid, the "sub" claim is missing, or no matching user is found.
    
    Returns:
        User: The authenticated user loaded from the database.
    
    Raises:
        fastapi.HTTPException: 401 Unauthorized for invalid token, missing user_id, or user not found.
    """
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    user_id: int = payload.get("sub")  # "sub" claim should hold the user id
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user_id",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
