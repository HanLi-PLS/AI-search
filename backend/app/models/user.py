"""
User model for authentication
"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime
from sqlalchemy.sql import func
from backend.app.database import Base
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    """
    User model for authentication and authorization
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)

    # Authorization
    is_approved = Column(Boolean, default=False)  # Admin must approve new users
    is_admin = Column(Boolean, default=False)

    # Password reset
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, approved={self.is_approved})>"

    def set_password(self, password: str):
        """Hash and set password"""
        self.password_hash = pwd_context.hash(password)

    def check_password(self, password: str) -> bool:
        """Verify password"""
        return pwd_context.verify(password, self.password_hash)

    def to_dict(self):
        """Convert to dictionary (excluding sensitive fields)"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'is_approved': self.is_approved,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }
