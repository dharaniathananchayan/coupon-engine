from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime
from app.database import Base


class Staff(Base):
    __tablename__ = "staff"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<Staff(email='{self.email}')>"
