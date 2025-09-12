import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    DateTime,
    func,
    Boolean,
    Integer,
    Float,  # Imported Float
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
#from utils import generate_otp

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(128))
    is_verified = Column(Boolean, default=False, nullable=False)

class EmailOTP(Base):
    __tablename__ = "email_otps"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def is_expired(self):
        return datetime.utcnow() > self.expires_at


class Expense(Base):
    __tablename__ = 'expenses'

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False) # Float is now imported
    description = Column(String(255))
    category = Column(String(50))
    date = Column(DateTime)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="expenses")

# Define the relationship on the User class after Expense is defined
User.expenses = relationship("Expense", order_by=Expense.id, back_populates="user")
