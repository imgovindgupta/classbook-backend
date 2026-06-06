# ============================================================
# CLASSBOOK BACKEND — main.py
# Simple FastAPI app connected to Supabase
# All routes in one file — easy to read and understand
# ============================================================

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client
from dotenv import load_dotenv
from typing import Optional
import os
import smtplib
from email.mime.text import MIMEText

load_dotenv()

# ── Supabase credentials from .env ───────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

# ── FastAPI app setup ────────────────────────────────────────
app = FastAPI(
    title="ClassBook API",
    description="Simple Attendance and Gradebook API",
    version="1.0.0"
)

# CORS — allows frontend (Lovable) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def db(token: str):
    """
    Creates a Supabase client using the teacher's JWT token.
    This ensures RLS (Row Level Security) is applied —
    so each teacher only sees their own data.
    """
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    client.postgrest.auth(token)
    return client


def extract_token(authorization: str):
    """
    Pulls the token out of the Authorization header.
    Frontend sends: Authorization: Bearer <token>
    We extract just the token part.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    return authorization.replace("Bearer ", "")


# ============================================================
# PYDANTIC MODELS (request body shapes)
# ============================================================

class RegisterData(BaseModel):
    full_name: str
    email: str
    password: str

class LoginData(BaseModel):
    email: str
    password: str

class ClassData(BaseModel):
    name: str
    subject: str
    section: Optional[str] = ""
    academic_year: Optional[str] = "2024-25"

class StudentData(BaseModel):
    class_id: str
    full_name: str
    roll_number: str
    parent_email: Optional[str] = ""

class SessionData(BaseModel):
    class_id: str
    session_date: str   # format: "2024-08-01"
    topic: Optional[str] = ""

class AttendanceRecord(BaseModel):
    student_id: str
    status: str         # "present", "absent", or "late"

class BulkAttendance(BaseModel):
    session_id: str
    records: list[AttendanceRecord]

class AssessmentData(BaseModel):
    class_id: str
    name: str
    assessment_type: str  # quiz / assignment / midterm / final / project
    max_marks: float
    weight_percent: float
    conducted_on: Optional[str] = None

class GradeData(BaseModel):
    student_id: str
    assessment_id: str
    marks_obtained: float
    remarks: Optional[str] = ""


# ============================================================
# ROUTE 1 — ROOT (health check)
# ============================================================

@app.get("/")
def root():
    return {
        "message": "ClassBook API is live!",
        "status": "running",
        "docs": "/docs"
    }


# ============================================================
# ROUTE GROUP 2 — AUTH
# ============================================================

@app.post("/auth/register")
def register(data: RegisterData):
    """Register a new teacher account"""
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        res = client.auth.sign_up({
            "email": data.email,
            "password": data.password,
            "options": {
                "data": {"full_name": data.full_name}
            }
        })
        return {
            "message": "Registered successfully! Please verify your email.",
            "user_id": res.user.id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
def login(data: LoginData):
    """Login and receive access token"""
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        res = client.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password
        })
        return {
            "access_token": res.session.access_token,
            "teacher_id": res.user.id,
            "email": res.user.email
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid email or password")


# ============================================================
# ROUTE GROUP 3 — CLASSES
# ============================================================

@app.get("/classes")
def get_all_classes(authorization: str = Header(...)):
    """Get all classes belonging to the logged-in teacher"""
    token = extract_token(authorization)
    try:
        res = db(token).table("classes").select("*").execute()
        return {"classes": res.data, "total": len(res.data)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/classes")
def create_class(data: ClassData, authorization: str = Header(...)):
    """Create a new class"""
    token = extract_token(authorization)
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        teacher = client.auth.get_user(token)

        res = db(token).table("classes").insert({
            "teacher_id": teacher.user.id,
            "name": data.name,
            "subject": data.subject,
            "section": data.section,
            "academic_year": data.academic_year
        }).execute()

        return {"message": "Class created!", "class": res.data[0]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# ROUTE GROUP 4 — STUDENTS
# ============================================================

@app.get("/classes/{class_id}/students")
def get_students(class_id: str, authorization: str = Header(...)):
    """Get all students in a class"""
    token = extract_token(authorization)
    try:
        res = (db(token).table("students")
               .select("*")
               .eq("class_id", class_id)
               .order("roll_number")
               .execute())
        return {"students": res.data, "total": len(res.data)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/students")
def add_student(data: StudentData, authorization: str = Header(...)):
    """Add a student to a class"""
    token = extract_token(authorization)
    try:
        res = db(token).table("students").insert({
            "class_id": data.class_id,
            "full_name": data.full_name,
            "roll_number": data.roll_number,
            "parent_email": data.parent_email
        }).execute()
        return {"message": "Student added!", "student": res.data[0]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# ROUTE GROUP 5 — SESSIONS
# ============================================================

@app.post("/sessions")
def create_session(data: SessionData, authorization: str = Header(...)):
    """Create a class session (one per lecture day)"""
    token = extract_token(authorization)
    try:
        res = db(token).table("sessions").insert({
            "class_id": data.class_id,
            "session_date": data.session_date,
            "topic": data.topic
        }).execute()
        return {"message": "Session created!", "session": res.data[0]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/classes/{class_id}/sessions")
def get_sessions(class_id: str, authorization: str = Header(...)):
    """Get all sessions for a class"""
    token = extract_token(authorization)
    try:
        res = (db(token).table("sessions")
               .select("*")
               .eq("class_id", class_id)
               .order("session_date", desc=True)
               .execute())
        return {"sessions": res.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# ROUTE GROUP 6 — ATTENDANCE
# ============================================================

@app.post("/attendance")
def mark_attendance(data: BulkAttendance, authorization: str = Header(...)):
    """
    Mark attendance for all students in one session.
    Sends a list of student_id + status records together.
    Uses upsert so re-submitting updates existing records.
    """
    token = extract_token(authorization)
    try:
        records = [
            {
                "session_id": data.session_id,
                "student_id": r.student_id,
                "status": r.status
            }
            for r in data.records
        ]
        db(token).table("attendance").upsert(
            records,
            on_conflict="session_id,student_id"
        ).execute()

        return {"message": f"Attendance saved for {len(records)} students"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# ROUTE GROUP 7 — ASSESSMENTS
# ============================================================

@app.post("/assessments")
def create_assessment(data: AssessmentData, authorization: str = Header(...)):
    """Create an assessment (quiz, midterm, final, etc.)"""
    token = extract_token(authorization)
    try:
        res = db(token).table("assessments").insert({
            "class_id": data.class_id,
            "name": data.name,
            "assessment_type": data.assessment_type,
            "max_marks": data.max_marks,
            "weight_percent": data.weight_percent,
            "conducted_on": data.conducted_on
        }).execute()
        return {"message": "Assessment created!", "assessment": res.data[0]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/classes/{class_id}/assessments")
def get_assessments(class_id: str, authorization: str = Header(...)):
    """Get all assessments for a class"""
    token = extract_token(authorization)
    try:
        res = (db(token).table("assessments")
               .select("*")
               .eq("class_id", class_id)
               .execute())
        return {"assessments": res.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# ROUTE GROUP 8 — GRADES
# ============================================================

@app.post("/grades")
def save_grade(data: GradeData, authorization: str = Header(...)):
    """
    Save or update a student's grade for an assessment.
    Uses upsert — safe to call multiple times.
    """
    token = extract_token(authorization)
    try:
        res = db(token).table("grades").upsert({
            "student_id": data.student_id,
            "assessment_id": data.assessment_id,
            "marks_obtained": data.marks_obtained,
            "remarks": data.remarks
        }, on_conflict="student_id,assessment_id").execute()
        return {"message": "Grade saved!", "grade": res.data[0]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# ROUTE GROUP 9 — REPORT (uses our SQL views from Phase 1)
# ============================================================

@app.get("/report/{student_id}")
def get_report(student_id: str, authorization: str = Header(...)):
    """
    Full report for one student.
    Pulls from the two views we created in Phase 1:
      - student_attendance_summary
      - student_grade_summary
    """
    token = extract_token(authorization)
    try:
        student    = (db(token).table("students")
                      .select("*, classes(name, subject)")
                      .eq("id", student_id)
                      .single().execute())

        attendance = (db(token).table("student_attendance_summary")
                      .select("*")
                      .eq("student_id", student_id)
                      .execute())

        grades     = (db(token).table("student_grade_summary")
                      .select("*")
                      .eq("student_id", student_id)
                      .execute())

        return {
            "student"    : student.data,
            "attendance" : attendance.data[0] if attendance.data else {},
            "grades"     : grades.data[0]     if grades.data     else {}
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# ROUTE GROUP 10 — EMAIL PARENT
# ============================================================

@app.post("/email/{student_id}")
def send_parent_email(student_id: str, authorization: str = Header(...)):
    """Send a progress report email to the student's parent"""
    token = extract_token(authorization)
    try:
        student    = (db(token).table("students")
                      .select("*, classes(name, subject)")
                      .eq("id", student_id)
                      .single().execute())

        attendance = (db(token).table("student_attendance_summary")
                      .select("*")
                      .eq("student_id", student_id)
                      .execute())

        grades     = (db(token).table("student_grade_summary")
                      .select("*")
                      .eq("student_id", student_id)
                      .execute())

        s = student.data
        parent_email = s.get("parent_email", "")

        if not parent_email:
            raise HTTPException(status_code=400, detail="No parent email on file")

        att_pct   = attendance.data[0].get("attendance_percentage", 0) if attendance.data else 0
        final_pct = grades.data[0].get("final_percentage", 0)          if grades.data     else 0

        # Simple plain-text email body
        body = f"""Dear Parent / Guardian,

This is a progress update for your child.

Student    : {s['full_name']}
Roll No    : {s['roll_number']}
Class      : {s['classes']['name']} — {s['classes']['subject']}

Final Grade   : {final_pct}%
Attendance    : {att_pct}%

For questions, please contact the teacher directly.

Regards,
ClassBook Academic System"""

        msg = MIMEText(body)
        msg["From"]    = os.getenv("SMTP_EMAIL")
        msg["To"]      = parent_email
        msg["Subject"] = f"Progress Report — {s['full_name']}"

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(os.getenv("SMTP_EMAIL"), os.getenv("SMTP_PASSWORD"))
        server.sendmail(os.getenv("SMTP_EMAIL"), parent_email, msg.as_string())
        server.quit()

        return {"message": f"Email sent to {parent_email}"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email failed: {str(e)}")