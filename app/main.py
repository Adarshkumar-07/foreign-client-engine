from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import json

from app.database import Base, engine, get_db
from app.models.lead import Lead

from app.services.website_checker import check_website
from app.services.lead_scorer import calculate_lead_score
from app.services.opportunity_analyzer import analyze_opportunity
from app.services.email_generator import generate_outreach_email
from app.services.lead_discovery import discover_leads
from app.services.contact_enricher import enrich_contact
from app.services.gmail_service import create_gmail_draft


app = FastAPI(
    title="Foreign Client Engine",
    description="Automated foreign client discovery and outreach system",
    version="0.4.0"
)

Base.metadata.create_all(bind=engine)


# ============================================================
# INPUT MODELS
# ============================================================

class LeadInput(BaseModel):
    business_name: str
    country: str
    city: str
    category: str
    website: str | None = None
    rating: float | None = None
    reviews: int | None = None


class DiscoveryInput(BaseModel):
    city: str
    country: str
    category: str

    limit: int = Field(
        default=10,
        ge=1,
        le=50
    )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

async def process_lead(
    lead_input: LeadInput,
    db: Session,
    phone: str | None = None,
    email: str | None = None,
    source: str | None = None
):
    website_data = await check_website(
        lead_input.website
    )

    scoring = calculate_lead_score(
        website_data=website_data,
        rating=lead_input.rating,
        reviews=lead_input.reviews
    )

    new_lead = Lead(
        business_name=lead_input.business_name,
        country=lead_input.country,
        city=lead_input.city,
        category=lead_input.category,

        website=lead_input.website,
        phone=phone,
        email=email,
        source=source,

        rating=lead_input.rating,
        reviews=lead_input.reviews,

        website_status=website_data.get("status"),
        lead_score=scoring.get("lead_score"),
        priority=scoring.get("priority"),

        recommended_service=scoring.get(
            "recommended_service"
        ),

        reasons=json.dumps(
            scoring.get("reasons", [])
        ),

        problems=json.dumps(
            website_data.get("problems", [])
        )
    )

    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)

    return new_lead, website_data, scoring


def lead_to_dict(lead: Lead):

    return {
        "id": lead.id,
        "business_name": lead.business_name,
        "country": lead.country,
        "city": lead.city,
        "category": lead.category,

        "website": lead.website,
        "phone": lead.phone,
        "email": lead.email,
        "source": lead.source,

        "rating": lead.rating,
        "reviews": lead.reviews,

        "website_status": lead.website_status,
        "lead_score": lead.lead_score,
        "priority": lead.priority,

        "recommended_service": lead.recommended_service,

        "reasons": json.loads(
            lead.reasons or "[]"
        ),

        "problems": json.loads(
            lead.problems or "[]"
        )
    }


def build_lead_analysis(lead: Lead):

    website_data = {
        "status": lead.website_status,

        "problems": json.loads(
            lead.problems or "[]"
        )
    }

    scoring = {
        "lead_score": lead.lead_score,

        "priority": lead.priority,

        "recommended_service":
            lead.recommended_service,

        "reasons": json.loads(
            lead.reasons or "[]"
        )
    }

    return website_data, scoring


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():

    return {
        "message": "Foreign Client Engine is running",
        "version": "0.4.0",
        "status": "online"
    }


# ============================================================
# ANALYZE SINGLE LEAD
# ============================================================

@app.post("/api/leads/analyze")
async def analyze_lead(
    lead: LeadInput,
    db: Session = Depends(get_db)
):

    existing_lead = db.query(Lead).filter(
        Lead.business_name == lead.business_name,
        Lead.city == lead.city,
        Lead.country == lead.country
    ).first()

    if existing_lead:

        return {
            "message": "Lead already exists",
            "duplicate": True,
            "lead": lead_to_dict(existing_lead)
        }

    new_lead, website_data, scoring = await process_lead(
        lead,
        db
    )

    return {
        "duplicate": False,
        "lead_id": new_lead.id,

        "business": {
            "name": new_lead.business_name,
            "country": new_lead.country,
            "city": new_lead.city,
            "category": new_lead.category
        },

        "website_analysis": website_data,
        "lead_analysis": scoring
    }


# ============================================================
# GET ALL LEADS
# ============================================================

@app.get("/api/leads")
def get_leads(
    db: Session = Depends(get_db)
):

    leads = db.query(Lead).order_by(
        Lead.lead_score.desc()
    ).all()

    return [
        lead_to_dict(lead)
        for lead in leads
    ]


# ============================================================
# GET HIGH PRIORITY LEADS
# ============================================================

@app.get("/api/leads/high-priority")
def get_high_priority_leads(
    db: Session = Depends(get_db)
):

    leads = db.query(Lead).filter(
        Lead.priority.in_(
            ["HIGH", "VERY_HIGH"]
        )
    ).order_by(
        Lead.lead_score.desc()
    ).all()

    return [
        lead_to_dict(lead)
        for lead in leads
    ]


# ============================================================
# GET SINGLE LEAD
# ============================================================

@app.get("/api/leads/{lead_id}")
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db)
):

    lead = db.query(Lead).filter(
        Lead.id == lead_id
    ).first()

    if not lead:

        raise HTTPException(
            status_code=404,
            detail="Lead not found"
        )

    return lead_to_dict(lead)


# ============================================================
# GENERATE OUTREACH
# ============================================================

@app.get("/api/leads/{lead_id}/outreach")
async def generate_lead_outreach(
    lead_id: int,
    db: Session = Depends(get_db)
):

    lead = db.query(Lead).filter(
        Lead.id == lead_id
    ).first()

    if not lead:

        raise HTTPException(
            status_code=404,
            detail="Lead not found"
        )

    website_data, scoring = build_lead_analysis(
        lead
    )

    opportunity = analyze_opportunity(
        lead,
        website_data,
        scoring
    )

    email = generate_outreach_email(
        lead,
        opportunity
    )

    return {
        "lead_id": lead.id,
        "business_name": lead.business_name,

        "opportunity_report": opportunity,

        "outreach_email": email
    }


# ============================================================
# CONTACT ENRICHMENT
# ============================================================

@app.post("/api/leads/{lead_id}/enrich-contact")
async def enrich_lead_contact(
    lead_id: int,
    db: Session = Depends(get_db)
):

    lead = db.query(Lead).filter(
        Lead.id == lead_id
    ).first()

    if not lead:

        raise HTTPException(
            status_code=404,
            detail="Lead not found"
        )

    if not lead.website:

        return {
            "lead_id": lead.id,
            "business_name": lead.business_name,
            "status": "NO_WEBSITE",

            "message": (
                "Contact enrichment requires an "
                "official website."
            )
        }

    contact_data = await enrich_contact(
        lead.website
    )

    if contact_data.get("email"):
        lead.email = contact_data["email"]

    if contact_data.get("phone"):
        lead.phone = contact_data["phone"]

    db.commit()
    db.refresh(lead)

    return {
        "lead_id": lead.id,
        "business_name": lead.business_name,

        "contact_enrichment": contact_data,

        "saved_contact": {
            "email": lead.email,
            "phone": lead.phone
        }
    }


# ============================================================
# CREATE GMAIL DRAFT
# ============================================================

@app.post("/api/leads/{lead_id}/gmail-draft")
async def create_lead_gmail_draft(
    lead_id: int,
    db: Session = Depends(get_db)
):

    lead = db.query(Lead).filter(
        Lead.id == lead_id
    ).first()

    if not lead:

        raise HTTPException(
            status_code=404,
            detail="Lead not found"
        )

    if not lead.email:

        raise HTTPException(
            status_code=400,
            detail=(
                "No email found for this lead. "
                "Run contact enrichment first."
            )
        )

    website_data, scoring = build_lead_analysis(
        lead
    )

    opportunity = analyze_opportunity(
        lead,
        website_data,
        scoring
    )

    outreach = generate_outreach_email(
        lead,
        opportunity
    )

    draft_result = create_gmail_draft(
        recipient=lead.email,
        subject=outreach["subject"],
        body=outreach["body"]
    )

    return {
        "lead_id": lead.id,

        "business_name": lead.business_name,

        "email": lead.email,

        "gmail_draft": draft_result
    }


# ============================================================
# DISCOVER + ANALYZE + SAVE LEADS
# ============================================================

@app.post("/api/leads/discover")
async def discover_business_leads(
    request: DiscoveryInput,
    db: Session = Depends(get_db)
):

    discovered_leads = await discover_leads(
        city=request.city,
        country=request.country,
        category=request.category,
        limit=request.limit
    )

    if isinstance(discovered_leads, dict):

        if "error" in discovered_leads:

            raise HTTPException(
                status_code=500,
                detail=discovered_leads["error"]
            )

    results = []

    for discovered in discovered_leads:

        business_name = discovered.get(
            "business_name"
        )

        if not business_name:
            continue

        existing_lead = db.query(Lead).filter(
            Lead.business_name == business_name,
            Lead.city == request.city,
            Lead.country == request.country
        ).first()

        if existing_lead:

            results.append({
                "business_name": business_name,
                "status": "ALREADY_EXISTS",
                "lead_id": existing_lead.id
            })

            continue

        lead_input = LeadInput(
            business_name=business_name,
            country=request.country,
            city=request.city,
            category=request.category,
            website=discovered.get("website"),
            rating=None,
            reviews=None
        )

        try:

            new_lead, website_data, scoring = (
                await process_lead(
                    lead_input,
                    db,
                    phone=discovered.get("phone"),
                    email=discovered.get("email"),
                    source=discovered.get("source")
                )
            )

            results.append({
                "business_name": new_lead.business_name,

                "status": "SAVED",

                "lead_id": new_lead.id,

                "website_status":
                    new_lead.website_status,

                "lead_score":
                    new_lead.lead_score,

                "priority":
                    new_lead.priority,

                "phone_found":
                    bool(new_lead.phone),

                "email_found":
                    bool(new_lead.email)
            })

        except Exception as error:

            results.append({
                "business_name": business_name,
                "status": "FAILED",
                "error": str(error)
            })

    saved = len([
        item for item in results
        if item["status"] == "SAVED"
    ])

    duplicates = len([
        item for item in results
        if item["status"] == "ALREADY_EXISTS"
    ])

    failed = len([
        item for item in results
        if item["status"] == "FAILED"
    ])

    return {
        "city": request.city,
        "country": request.country,
        "category": request.category,

        "total_discovered":
            len(discovered_leads),

        "saved": saved,

        "duplicates": duplicates,

        "failed": failed,

        "results": results
    }