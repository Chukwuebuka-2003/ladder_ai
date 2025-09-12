# /home/type-shit/expense_tracker/app/schemas.py
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

# User Schemas
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserVerify(BaseModel):
    email: EmailStr # Verified by email
    otp: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer" # Added default token_type

# Login Schema
class LoginSchema(BaseModel):
    email: EmailStr
    password: str

# --- NEW: Schemas for Auth ---
class UserProfileResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    is_verified: bool

    class Config:
        orm_mode = True

class AuthResponse(BaseModel):
    user: UserProfileResponse # Changed to UserProfileResponse
    access_token: str
    token_type: str = "bearer" # Added default token_type

# Schemas for OTP
class OTPRequest(BaseModel):
    email: EmailStr

class OTPResponse(BaseModel):
    message: str

class OTPVerify(BaseModel):
    email: EmailStr
    code: str
# --- End of NEW Schemas for Auth ---


# Expense Schemas
class ExpenseBase(BaseModel):
    amount: float
    description: str
    category: Optional[str] = None # Make category optional
    date: datetime

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseUpdate(BaseModel):
    amount: Optional[float] = None
    description: Optional[str] = None
    category: Optional[str] = None # Make category optional
    date: Optional[datetime] = None

class ExpenseResponse(ExpenseBase):
    id: int
    user_id: int

    class Config:
        orm_mode = True

# AI Schemas

class AIProvider(str, Enum):
    GEMINI = "gemini"
    GROQ = "groq"


class ExpenseDetails(BaseModel):
    amount: float
    description: str
    date: datetime

class CategorizeRequest(BaseModel):
    expense_details: ExpenseDetails
    ai_provider: AIProvider = AIProvider.GEMINI

class InsightsRequest(BaseModel):
    start_date: datetime
    end_date: datetime

class InsightsRequestWithProvider(InsightsRequest):
    ai_provider: AIProvider = AIProvider.GROQ

# --- MODIFIED: New schema for TopCategory and updated InsightsResponse ---
class TopCategory(BaseModel):
    category: str
    amount: float

class InsightsResponse(BaseModel):
    total_spent: float
    top_categories: List[TopCategory] # Changed to List[TopCategory]
    anomalies: List[Dict[str, Any]]
# --- End of MODIFIED Schemas ---

# --- NEW: SignupRequest Schema ---
# Assuming SignupRequest is needed for the /signup endpoint
class SignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
# --- End of NEW SignupRequest ---
