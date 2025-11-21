import os
import smtplib
from email.mime.text import MIMEText
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

from database import create_document, db

app = FastAPI(title="SamEst Web Dev API", description="Backend for contact form and content")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ContactPayload(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    phone: Optional[str] = None
    service: Optional[str] = Field(None, description="Service interested in")
    message: Optional[str] = Field(None, max_length=5000)


@app.get("/")
def read_root():
    return {"message": "SamEst Web Dev API running"}


@app.post("/contact")
def submit_contact(payload: ContactPayload):
    # Save to database for persistence
    try:
        create_document("contactsubmission", payload.model_dump())
    except Exception as e:
        # Don't fail the request if DB is not available; continue to email attempt
        pass

    # Attempt to send email if SMTP is configured
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    to_email = os.getenv("TO_EMAIL", "contact@samestwebdev.com")
    from_email = os.getenv("FROM_EMAIL", smtp_user or "no-reply@samestwebdev.com")

    email_sent = False
    if smtp_host and to_email:
        subject = f"New Contact Form: {payload.name} ({payload.service or 'General'})"
        body = f"""
New contact submission from SamEst Web Dev website

Name: {payload.name}
Email: {payload.email}
Phone: {payload.phone or '-'}
Service: {payload.service or '-'}

Message:\n{payload.message or '-'}
"""
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email
        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.starttls()
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.sendmail(from_email, [to_email], msg.as_string())
            email_sent = True
        except Exception:
            email_sent = False

    return {
        "ok": True,
        "email_sent": email_sent,
        "message": "Thanks! Your message has been received. We'll get back to you shortly."
    }


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
