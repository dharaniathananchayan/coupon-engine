from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class Redemption(Base):
    __tablename__ = "redemptions"
    __table_args__ = (
        CheckConstraint("base_price >= 0", name="chk_base_price"),
        CheckConstraint("discounted_price >= 0", name="chk_discounted_price"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    coupon_id = Column(String(36), ForeignKey("coupons.id", ondelete="RESTRICT"), nullable=False, index=True)
    base_price = Column(Float, nullable=False)
    discounted_price = Column(Float, nullable=False)
    redeemed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    coupon = relationship("Coupon", back_populates="redemptions")

    def __repr__(self):
        return f"<Redemption(coupon_id='{self.coupon_id}', base={self.base_price}, discounted={self.discounted_price})>"
