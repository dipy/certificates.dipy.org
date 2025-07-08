from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=True)
    full_name = Column(String, nullable=True)

    # Authentication fields
    github_id = Column(String, unique=True, index=True, nullable=True)
    google_id = Column(String, unique=True, index=True, nullable=True)
    linkedin_id = Column(String, unique=True, index=True, nullable=True)

    # Profile fields
    avatar_url = Column(String, nullable=True)
    github_username = Column(String, nullable=True)
    linkedin_username = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sponsorships = relationship("Sponsorship", back_populates="user")

    @property
    def auth_method(self):
        """Return the primary authentication method used"""
        if self.github_id:
            return "github"
        elif self.google_id:
            return "google"
        elif self.linkedin_id:
            return "linkedin"
        return None


class Sponsorship(Base):
    __tablename__ = "sponsorships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Plan details
    plan_type = Column(String, nullable=False)  # "individual" or "team"
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")

    # Payment details
    payment_id = Column(String, unique=True, index=True)  # FlexPay payment ID
    payment_status = Column(String, default="pending")  # pending, completed, failed
    invoice_url = Column(String, nullable=True)
    transaction_id = Column(String, unique=True, index=True, nullable=True)  # FlexPay final transaction ID

    # Team plan specific
    team_size = Column(Integer, default=1)  # Number of users for team plan

    # GitHub integration
    github_sponsor_id = Column(String, nullable=True)  # GitHub sponsor ID if created

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="sponsorships")

    def __init__(self, **kwargs):
        if not kwargs.get('payment_id'):
            kwargs['payment_id'] = str(uuid.uuid4())
        super().__init__(**kwargs)