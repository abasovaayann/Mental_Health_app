from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "app_users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # Demographic information
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    degree = Column(String, nullable=True)
    university = Column(String, nullable=True)
    city = Column(String, nullable=True)
    country = Column(String, nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    baseline_completed = Column(Boolean, default=False, nullable=False)
    baseline_completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<User {self.email}>"
