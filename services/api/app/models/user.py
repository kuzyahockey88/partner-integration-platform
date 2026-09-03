from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
import enum
from ..core.database import Base

class UserRole(str, enum.Enum):
    PARTNER = "partner"
    MANAGER = "manager"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.PARTNER)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    operations = relationship("IntegrationOperation", back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.username} [{self.role}]>"