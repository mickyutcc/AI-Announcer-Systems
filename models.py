
from datetime import datetime, timedelta
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Enum, Boolean, ForeignKey
)
from database_setup import Base

class SubscriptionStatus:
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    # We only need enough definition for the ForeignKey to work. 
    # The actual table is created by user_db.py via raw SQL.
    # By extending Base, create_all might try to create it, but checkfirst=True is default.
    # However, since it exists, it should be fine.

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan = Column(String(64), nullable=False)  # 'easy'/'standard'/'pro'
    status = Column(Enum(SubscriptionStatus.PENDING, SubscriptionStatus.ACTIVE,
                        SubscriptionStatus.PAST_DUE, SubscriptionStatus.CANCELLED,
                        SubscriptionStatus.EXPIRED, SubscriptionStatus.REJECTED, name="subscription_status"),
                    default=SubscriptionStatus.PENDING)
    # manual payment fields
    payment_amount = Column(Integer, nullable=True)  # amount in THB recorded by admin (optional)
    payment_ref = Column(String(128), nullable=True)  # bank ref / transfer id from user
    proof_path = Column(Text, nullable=True)  # path or URL to slip
    # subscription period
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    gateway_subscription_id = Column(String(128), nullable=True)  # for future gateway mapping
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_by = Column(Integer, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_by = Column(Integer, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    reject_reason = Column(Text, nullable=True)

    def activate_for_period(self, days: int = 30):
        now = datetime.utcnow()
        self.current_period_start = now
        self.current_period_end = now + timedelta(days=days)
        self.status = SubscriptionStatus.ACTIVE
