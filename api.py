from fastapi import FastAPI
from pydantic import BaseModel

from auth import login_user, register_user
from ai_engine import generate_with_fallback
from config import GEMINI_TEXT_MODELS

from database import (
    dashboard_stats,
    doctor_queue,
    get_patient_records
)

app = FastAPI(
    title="CareConnect AI Pro API",
    version="1.0"
)


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    phone: str
    password: str
    role: str


class ChatRequest(BaseModel):
    question: str


@app.get("/")
def home():
    return {
        "message": "CareConnect AI Pro Backend Running"
    }


@app.get("/health")
def health():
    return {
        "status": "OK"
    }


@app.post("/login")
def login(data: LoginRequest):

    user = login_user(
        data.email,
        data.password
    )

    if user:
        return {
            "success": True,
            "user": user
        }

    return {
        "success": False,
        "message": "Invalid credentials"
    }


@app.post("/register")
def register(data: RegisterRequest):

    success, message = register_user(
        data.name,
        data.email,
        data.phone,
        data.password,
        data.role
    )

    return {
        "success": success,
        "message": message
    }


@app.get("/dashboard-stats")
def get_dashboard_stats():

    stats = dashboard_stats()

    return {
        "total_users": len(stats["users"]),
        "total_assessments": len(stats["assessments"]),
        "total_appointments": len(stats["appointments"]),
        "total_prescriptions": len(stats["prescriptions"]),
        "total_feedback": len(stats["feedback"]),
        "total_reminders": len(stats["reminders"]),
        "total_followups": len(stats["followups"])
    }


@app.get("/doctor-queue")
def get_doctor_queue():

    queue = doctor_queue()

    return queue.to_dict(orient="records")


@app.get("/patient-records/{user_id}")
def patient_records(user_id: int):

    assessments, appointments, reminders, followups, prescriptions = (
        get_patient_records(user_id)
    )

    return {
        "assessments": assessments.to_dict(orient="records"),
        "appointments": appointments.to_dict(orient="records"),
        "reminders": reminders.to_dict(orient="records"),
        "followups": followups.to_dict(orient="records"),
        "prescriptions": prescriptions.to_dict(orient="records")
    }


@app.post("/chatbot")
def chatbot(data: ChatRequest):

    prompt = f"""
You are CareConnect AI Pro.

Answer this healthcare question safely.
Do not provide a final diagnosis.

Question:
{data.question}
"""

    try:

        answer = generate_with_fallback(
            prompt,
            GEMINI_TEXT_MODELS
        )

        return {
            "success": True,
            "answer": answer
        }

    except Exception as e:

        return {
            "success": False,
            "message": str(e)
        }