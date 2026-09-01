from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from io import BytesIO
from urllib.parse import quote
import json
import os

from openpyxl import Workbook

from app.database import Base, engine, get_db
from app.models.lead import Lead
from app.models.activity_log import ActivityLog

from app.services.website_checker import check_website
from app.services.lead_scorer import calculate_lead_score
from app.services.opportunity_analyzer import analyze_opportunity
from app.services.email_generator import generate_outreach_email
from app.services.lead_discovery import discover_leads
from app.services.contact_enricher import enrich_contact
from app.services.gmail_service import create_gmail_draft, send_gmail_message, get_authorization_url, complete_authorization, gmail_is_connected


app = FastAPI(
    title="Foreign Client Engine",
    description="Foreign client discovery, analysis and Gmail outreach system",
    version="0.6.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

Base.metadata.create_all(bind=engine)


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
    limit: int = Field(default=10, ge=1, le=50)


class EmailInput(BaseModel):
    subject: str | None = None
    body: str | None = None


oauth_state: str | None = None


def add_activity(db: Session, lead: Lead | None, action: str, status: str | None = None, recipient: str | None = None, subject: str | None = None, details: str | None = None):
    log = ActivityLog(
        lead_id=lead.id if lead else None,
        business_name=lead.business_name if lead else None,
        action=action,
        status=status,
        recipient=recipient,
        subject=subject,
        details=details,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


async def process_lead(lead_input: LeadInput, db: Session, phone: str | None = None, email: str | None = None, source: str | None = None):
    website_data = await check_website(lead_input.website)
    scoring = calculate_lead_score(website_data=website_data, rating=lead_input.rating, reviews=lead_input.reviews)

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
        recommended_service=scoring.get("recommended_service"),
        reasons=json.dumps(scoring.get("reasons", [])),
        problems=json.dumps(website_data.get("problems", [])),
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
        "reasons": json.loads(lead.reasons or "[]"),
        "problems": json.loads(lead.problems or "[]"),
    }


def build_lead_analysis(lead: Lead):
    website_data = {"status": lead.website_status, "problems": json.loads(lead.problems or "[]")}
    scoring = {
        "lead_score": lead.lead_score,
        "priority": lead.priority,
        "recommended_service": lead.recommended_service,
        "reasons": json.loads(lead.reasons or "[]"),
    }
    return website_data, scoring


def get_outreach(lead: Lead):
    website_data, scoring = build_lead_analysis(lead)
    opportunity = analyze_opportunity(lead, website_data, scoring)
    return opportunity, generate_outreach_email(lead, opportunity)


@app.get("/")
def home():
    return {"message": "Foreign Client Engine is running", "version": "0.6.1", "status": "online"}


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "foreign-client-engine"}


@app.post("/api/leads/analyze")
async def analyze_lead(lead: LeadInput, db: Session = Depends(get_db)):
    existing_lead = db.query(Lead).filter(Lead.business_name == lead.business_name, Lead.city == lead.city, Lead.country == lead.country).first()
    if existing_lead:
        return {"message": "Lead already exists", "duplicate": True, "lead": lead_to_dict(existing_lead)}

    new_lead, website_data, scoring = await process_lead(lead, db)
    add_activity(db, new_lead, "LEAD_ANALYZED", "COMPLETED")
    return {
        "duplicate": False,
        "lead_id": new_lead.id,
        "business": {"name": new_lead.business_name, "country": new_lead.country, "city": new_lead.city, "category": new_lead.category},
        "website_analysis": website_data,
        "lead_analysis": scoring,
    }


@app.get("/api/leads")
def get_leads(city: str | None = None, country: str | None = None, category: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Lead)
    if city:
        query = query.filter(Lead.city.ilike(city))
    if country:
        query = query.filter(Lead.country.ilike(country))
    if category:
        query = query.filter(Lead.category.ilike(category))
    leads = query.order_by(Lead.lead_score.desc()).all()
    return [lead_to_dict(lead) for lead in leads]


@app.get("/api/leads/high-priority")
def get_high_priority_leads(db: Session = Depends(get_db)):
    leads = db.query(Lead).filter(Lead.priority.in_(["HIGH", "VERY_HIGH"])).order_by(Lead.lead_score.desc()).all()
    return [lead_to_dict(lead) for lead in leads]


@app.get("/api/leads/{lead_id}")
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead_to_dict(lead)


@app.get("/api/leads/{lead_id}/outreach")
async def generate_lead_outreach(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    opportunity, email = get_outreach(lead)
    add_activity(db, lead, "EMAIL_GENERATED", "READY", lead.email, email.get("subject"))
    return {"lead_id": lead.id, "business_name": lead.business_name, "opportunity_report": opportunity, "outreach_email": email}


@app.post("/api/leads/{lead_id}/enrich-contact")
async def enrich_lead_contact(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not lead.website:
        return {"lead_id": lead.id, "business_name": lead.business_name, "status": "NO_WEBSITE", "message": "Contact enrichment requires an official website."}

    contact_data = await enrich_contact(lead.website)
    if contact_data.get("email"):
        lead.email = contact_data["email"]
    if contact_data.get("phone"):
        lead.phone = contact_data["phone"]
    db.commit()
    db.refresh(lead)
    add_activity(db, lead, "CONTACT_ENRICHMENT", "COMPLETED", lead.email, details=json.dumps(contact_data))
    return {"lead_id": lead.id, "business_name": lead.business_name, "contact_enrichment": contact_data, "saved_contact": {"email": lead.email, "phone": lead.phone}}


@app.get("/api/gmail/status")
def gmail_status():
    return gmail_is_connected()


@app.get("/api/gmail/login")
def gmail_login():
    global oauth_state
    try:
        authorization_url, state = get_authorization_url()
        oauth_state = state
        return RedirectResponse(authorization_url)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.get("/api/gmail/callback")
def gmail_callback(request: Request):
    global oauth_state
    error = request.query_params.get("error")
    if error:
        frontend_url = os.getenv("FRONTEND_URL")
        if frontend_url:
            return RedirectResponse(f"{frontend_url}?gmail=error&message={quote(error)}")
        return {"connected": False, "error": error}

    state = request.query_params.get("state")
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing OAuth authorization code")
    if oauth_state and state != oauth_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    try:
        result = complete_authorization(code)
        oauth_state = None
        frontend_url = os.getenv("FRONTEND_URL")
        if frontend_url:
            return RedirectResponse(f"{frontend_url}?gmail=connected")
        return {"message": "Gmail connected successfully", **result}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.post("/api/leads/{lead_id}/gmail-draft")
async def create_lead_gmail_draft(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not lead.email:
        raise HTTPException(status_code=400, detail="No email found for this lead. Run contact enrichment first.")

    _, outreach = get_outreach(lead)
    try:
        result = create_gmail_draft(lead.email, outreach["subject"], outreach["body"])
        add_activity(db, lead, "GMAIL_DRAFT", "DRAFT_CREATED", lead.email, outreach["subject"], json.dumps(result))
        return {"lead_id": lead.id, "business_name": lead.business_name, "email": lead.email, "gmail_draft": result}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.post("/api/leads/{lead_id}/send-email")
async def send_lead_email(lead_id: int, payload: EmailInput | None = None, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not lead.email:
        raise HTTPException(status_code=400, detail="No email found for this lead. Run contact enrichment first.")

    _, outreach = get_outreach(lead)
    subject = payload.subject if payload and payload.subject else outreach["subject"]
    body = payload.body if payload and payload.body else outreach["body"]

    try:
        result = send_gmail_message(lead.email, subject, body)
        add_activity(db, lead, "EMAIL_SENT", "SENT", lead.email, subject, json.dumps(result))
        return {"lead_id": lead.id, "business_name": lead.business_name, "email": lead.email, "send_result": result}
    except Exception as error:
        add_activity(db, lead, "EMAIL_SEND_FAILED", "FAILED", lead.email, subject, str(error))
        raise HTTPException(status_code=500, detail=str(error))


@app.post("/api/leads/discover")
async def discover_business_leads(request: DiscoveryInput, db: Session = Depends(get_db)):
    discovered_leads = await discover_leads(city=request.city, country=request.country, category=request.category, limit=request.limit)

    if isinstance(discovered_leads, dict) and "error" in discovered_leads:
        return {"city": request.city, "country": request.country, "category": request.category, "total_discovered": 0, "saved": 0, "duplicates": 0, "failed": 0, "results": [], "error": discovered_leads["error"]}

    results = []
    for discovered in discovered_leads:
        business_name = discovered.get("business_name")
        if not business_name:
            continue

        existing_lead = db.query(Lead).filter(Lead.business_name == business_name, Lead.city == request.city, Lead.country == request.country).first()
        if existing_lead:
            results.append({"business_name": business_name, "status": "ALREADY_EXISTS", "lead_id": existing_lead.id})
            continue

        lead_input = LeadInput(
            business_name=business_name,
            country=request.country,
            city=request.city,
            category=request.category,
            website=discovered.get("website"),
            rating=None,
            reviews=None,
        )

        try:
            new_lead, _, _ = await process_lead(lead_input, db, phone=discovered.get("phone"), email=discovered.get("email"), source=discovered.get("source"))
            add_activity(db, new_lead, "LEAD_DISCOVERED", "SAVED", new_lead.email)
            results.append({
                "business_name": new_lead.business_name,
                "status": "SAVED",
                "lead_id": new_lead.id,
                "website_status": new_lead.website_status,
                "lead_score": new_lead.lead_score,
                "priority": new_lead.priority,
                "phone_found": bool(new_lead.phone),
                "email_found": bool(new_lead.email),
            })
        except Exception as error:
            results.append({"business_name": business_name, "status": "FAILED", "error": str(error)})

    saved = sum(item["status"] == "SAVED" for item in results)
    duplicates = sum(item["status"] == "ALREADY_EXISTS" for item in results)
    failed = sum(item["status"] == "FAILED" for item in results)

    return {"city": request.city, "country": request.country, "category": request.category, "total_discovered": len(discovered_leads), "saved": saved, "duplicates": duplicates, "failed": failed, "results": results}


@app.get("/api/activity-logs")
def get_activity_logs(lead_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(ActivityLog)
    if lead_id is not None:
        query = query.filter(ActivityLog.lead_id == lead_id)
    logs = query.order_by(ActivityLog.created_at.desc()).all()
    return [{
        "id": log.id,
        "lead_id": log.lead_id,
        "business_name": log.business_name,
        "action": log.action,
        "status": log.status,
        "recipient": log.recipient,
        "subject": log.subject,
        "details": log.details,
        "created_at": log.created_at.isoformat(),
    } for log in logs]


@app.get("/api/activity-logs/export")
def export_activity_logs(db: Session = Depends(get_db)):
    logs = db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).all()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Activity Logs"
    sheet.append(["ID", "Lead ID", "Business Name", "Action", "Status", "Recipient", "Subject", "Details", "Created At"])

    for log in logs:
        sheet.append([log.id, log.lead_id, log.business_name, log.action, log.status, log.recipient, log.subject, log.details, log.created_at.isoformat()])

    for column in sheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column)
        sheet.column_dimensions[column[0].column_letter].width = min(max_length + 2, 50)

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="foreign_client_engine_logs.xlsx"'},
    )
