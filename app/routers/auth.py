from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import timedelta, datetime
from database import get_db
from models import User, EmailOTP

from schemas import (
    UserCreate,
    UserVerify,
    TokenResponse,
    LoginSchema,
    SignupRequest,
    UserProfileResponse,
    AuthResponse,
    OTPResponse,
    OTPRequest,
    OTPVerify
)

from utils import generate_otp

# Import necessary functions from auth_service
from services.auth_service import (
    get_password_hash,
    verify_password,
    create_access_token
)

from services.deps import get_current_user
from routers.email import send_otp_email

import logging
logger = logging.getLogger(__name__)

# ACCESS_TOKEN_EXPIRE_MINUTES is defined in auth_service, but keeping it here
# for clarity or if it's used elsewhere in this file. If not, it could be removed.
ACCESS_TOKEN_EXPIRE_MINUTES = 30
OTP_EXPIRY_MINUTES = 10 # Define OTP_EXPIRY_MINUTES before its first use

router = APIRouter()

# User-related routes
@router.post("/signup", response_model=OTPResponse, status_code=status.HTTP_201_CREATED)
async def signup(data: SignupRequest, db: Session = Depends(get_db)):
    """
    Create a new unverified user, generate and persist a time-limited email OTP, and send the OTP to the user's email.
    
    If a user with the given email or username already exists, raises HTTPException(status_code=409).
    
    Parameters:
        data (SignupRequest): Signup payload containing email, username, and plaintext password.
    
    Returns:
        dict: {"message": "User created. OTP sent."} on success.
    
    Side effects:
        - Inserts a new User with is_verified=False into the database.
        - Creates an EmailOTP row linked to the user's email with an expiration of OTP_EXPIRY_MINUTES.
        - Sends the OTP to the user's email address.
    """
    logger.info(f"Attempting signup for email: {data.email}, username: {data.username}")

    existing_user = db.query(User).filter(
        (User.email == data.email) | (User.username == data.username)
    ).first()
    if existing_user:
        logger.warning(f"Signup failed: User already exists with email {data.email} or username {data.username}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    user = User(
        email=data.email,
        username=data.username,
        hashed_password=get_password_hash(data.password),
        is_verified=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate and store OTP
    code = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    otp = EmailOTP(email=user.email, code=code, expires_at=expires_at)
    db.add(otp)
    db.commit()
    db.refresh(otp)

    # Send OTP via email
    send_otp_email(user.email, code, OTP_EXPIRY_MINUTES)
    logger.info(f"OTP email sent to {user.email} after signup. User needs to verify.")


    return {"message": "User created. OTP sent."}

@router.post("/login", response_model=TokenResponse)
async def login(data: LoginSchema, db: Session = Depends(get_db)):
    """
    Authenticate a user and return a JWT access token.
    
    Validates the provided credentials against the stored user record and requires the account to be verified. On success returns a TokenResponse containing a JWT with the user's id and username.
    
    Raises:
        HTTPException: 401 Unauthorized if credentials are invalid.
        HTTPException: 403 Forbidden if the account exists but is not verified.
    """
    logger.info(f"Attempting login for email: {data.email}")
    # Use User directly
    user = db.query(User).filter(User.email == data.email).first()
    # Use imported verify_password
    if not user or not verify_password(data.password, user.hashed_password):
        logger.warning(f"Login failed: Invalid credentials for email {data.email}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_verified: # Crucial: Check if user is verified
        logger.warning(f"Login failed: Account for email {data.email} is not verified.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not verified. Please check your email for verification."
        )

    # Use imported create_access_token
    access_token = create_access_token({"sub": user.id, "username": user.username})
    logger.info(f"User {user.username} logged in successfully.")
    return TokenResponse(access_token=access_token)


@router.post("/request-otp", response_model=OTPResponse)
async def request_otp(payload: OTPRequest, db: Session = Depends(get_db)):
    """
    Request a new one-time password (OTP) for the given email, invalidating any active OTPs and sending a fresh code via email.
    
    Looks up the user by payload.email and, if found, marks any currently unused/non-expired EmailOTP records for that email as used, creates and stores a new EmailOTP with a short expiry, and triggers sending the OTP email. Returns an OTPResponse confirming delivery.
    
    Parameters:
        payload (OTPRequest): Request body containing the target email (payload.email).
    
    Returns:
        OTPResponse: Message confirming that the OTP was sent.
    
    Raises:
        HTTPException (404): If no user exists with the provided email.
    """
    logger.info(f"Requesting OTP for email: {payload.email}")
    # Use User directly
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        logger.warning(f"OTP request failed: User with email {payload.email} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # Invalidate any active OTPs for this email first
    # Use EmailOTP directly
    db.query(EmailOTP).filter(
        EmailOTP.email == payload.email,
        EmailOTP.used == False,
        EmailOTP.expires_at > datetime.utcnow()
    ).update({"used": True})
    db.commit()

    code = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    otp = EmailOTP(email=payload.email, code=code, expires_at=expires_at) # Use EmailOTP directly
    db.add(otp)
    db.commit()
    db.refresh(otp)

    logger.info(f"OTP generated and stored for {payload.email}: {code}. Attempting to send email.")
    send_otp_email(payload.email, code, OTP_EXPIRY_MINUTES)
    logger.info(f"OTP email sending procedure initiated for {payload.email}.")
    return OTPResponse(message="OTP sent to your email")

@router.post("/verify-otp", response_model=OTPResponse)
async def verify_otp(payload: OTPVerify, db: Session = Depends(get_db)):
    """
    Verify a one-time password (OTP) for an email, mark the OTP as used, and set the user as verified.
    
    Searches for an unused, unexpired EmailOTP matching payload.email and payload.code. If found, marks that OTP as used, sets the corresponding User.is_verified to True (if the user record exists), commits the change, and returns a success message. If no valid OTP is found, raises HTTP 400.
    
    Parameters:
        payload (OTPVerify): Object containing `email` and `code` to verify.
        db (Session): Database session (injected dependency).
    
    Returns:
        OTPResponse: Message confirming successful verification.
    
    Raises:
        HTTPException(status_code=400): When the OTP is invalid or expired.
    """
    logger.info(f"Attempting to verify OTP for email: {payload.email}")
    # Use EmailOTP directly
    otp = db.query(EmailOTP).filter(
        EmailOTP.email == payload.email,
        EmailOTP.code == payload.code,
        EmailOTP.used == False,
        EmailOTP.expires_at > datetime.utcnow()
    ).first()
    if not otp:
        logger.warning(f"OTP verification failed: Invalid or expired OTP for email {payload.email}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP")

    otp.used = True

    # Mark user as verified upon successful OTP verification
    # Use User directly
    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        user.is_verified = True
        logger.info(f"User {user.email} has been successfully verified.")
    else:
        logger.error(f"Verified OTP for {payload.email} but user not found for verification update.")

    db.commit()
    logger.info(f"OTP for {payload.email} verified successfully.")
    return OTPResponse(message="OTP verified successfully. You can now log in.")

@router.post("/refresh-otp", response_model=OTPResponse)
async def refresh_otp(payload: OTPRequest, db: Session = Depends(get_db)):
    """
    Refresh the one-time password (OTP) for the given email, invalidate any active OTPs, store a new OTP, and send it by email.
    
    Given an OTPRequest containing an email address, this endpoint:
    - Verifies the user exists (raises HTTP 404 if not).
    - Marks any currently unused, unexpired OTPs for that email as used.
    - Generates a new OTP that expires after OTP_EXPIRY_MINUTES, saves it to EmailOTP, and sends it to the email address.
    - Returns an OTPResponse confirming that a new OTP was sent.
    
    Parameters:
        payload (OTPRequest): Request payload; uses payload.email as the target address.
    
    Returns:
        OTPResponse: Message confirming a new OTP was sent.
    
    Raises:
        HTTPException: 404 Not Found if no user exists for the provided email.
    """
    logger.info(f"Refreshing OTP for email: {payload.email}")
    # Use User directly
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        logger.warning(f"OTP refresh failed: User with email {payload.email} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # Use EmailOTP directly
    db.query(EmailOTP).filter(
        EmailOTP.email == payload.email,
        EmailOTP.used == False,
        EmailOTP.expires_at > datetime.utcnow()
    ).update({"used": True})
    db.commit()

    code = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    otp = EmailOTP(email=payload.email, code=code, expires_at=expires_at) # Use EmailOTP directly
    db.add(otp)
    db.commit()
    db.refresh(otp)

    logger.info(f"New OTP generated and stored for {payload.email}: {code}. Attempting to send email.")
    send_otp_email(payload.email, code, OTP_EXPIRY_MINUTES)
    logger.info(f"OTP refresh email sending procedure initiated for {payload.email}.")
    return OTPResponse(message="New OTP sent to your email")
