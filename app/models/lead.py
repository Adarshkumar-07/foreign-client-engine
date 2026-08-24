from sqlalchemy import Column, Integer, String, Float, Text

from app.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)

    business_name = Column(String, nullable=False)

    country = Column(String, nullable=False)
    city = Column(String, nullable=False)
    category = Column(String, nullable=False)

    website = Column(String, nullable=True)

    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)

    source = Column(String, nullable=True)

    rating = Column(Float, nullable=True)
    reviews = Column(Integer, nullable=True)

    website_status = Column(String, nullable=True)

    lead_score = Column(Integer, nullable=True)
    priority = Column(String, nullable=True)

    recommended_service = Column(
        String,
        nullable=True
    )

    reasons = Column(Text, nullable=True)
    problems = Column(Text, nullable=True)