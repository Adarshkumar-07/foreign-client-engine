from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime

from app.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, nullable=True, index=True)
    business_name = Column(String, nullable=True)
    action = Column(String, nullable=False)
    status = Column(String, nullable=True)
    recipient = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
