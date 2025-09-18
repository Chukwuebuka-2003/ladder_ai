import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    DateTime,
    func,
    Boolean,
    Integer,
    Float,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

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
    amount = Column(Float, nullable=False)
    description = Column(String(255))
    category = Column(String(50))
    date = Column(DateTime)
    user_id = Column(Integer, ForeignKey("users.id"))
    receipt_id = Column(String(255), index=True, nullable=True)
    receipt_group_id = Column(String(255), index=True, nullable=True)

    user = relationship("User", back_populates="expenses")

class Budget(Base):
    __tablename__ = 'budgets'

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="budgets")


# Define relationships on the User class
User.expenses = relationship("Expense", order_by=Expense.id, back_populates="user")
User.budgets = relationship("Budget", order_by=Budget.id, back_populates="user")
