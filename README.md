# ClassBook — Attendance & Gradebook App

ClassBook is a simple web app I built for teachers to manage student attendance and grades — without dealing with messy spreadsheets.

A teacher can log in, create their classes, add students, mark attendance for each session, enter assessment marks, and instantly see each student's final grade and attendance percentage. There's also a feature to send a quick progress email to parents.

---

## Why I Built This

This project was part of a Faculty Development Program (FDP) on Agentic AI. The goal was to build a real full-stack application using modern AI-assisted development tools — keeping the frontend and backend completely separate to understand the architecture clearly.

---

## What's Inside

The backend is a FastAPI app deployed on HuggingFace Spaces. It connects to a Supabase PostgreSQL database with proper authentication and row-level security — meaning each teacher only ever sees their own data.

The frontend is a React app built using Lovable, connected to the live backend API.

**Backend:** Python, FastAPI, Supabase, Docker  
**Frontend:** React (Lovable)  
**Deployed on:** HuggingFace Spaces + Lovable Hosting

---

## Live Links

- API: https://govindguptacontact-classbook-backend.hf.space
- API Docs: https://govindguptacontact-classbook-backend.hf.space/docs

---

## Project Files

```
classbook-backend/
├── main.py            ← all API routes in one place
├── requirements.txt
├── Dockerfile
└── .gitignore
```

Everything lives in `main.py` — kept intentionally simple and readable.

---

## Running Locally

```bash
git clone https://github.com/imgovindgupta/classbook-backend.git
cd classbook-backend
pip install -r requirements.txt
```

Create a `.env` file:
```
SUPABASE_URL=your-url
SUPABASE_ANON_KEY=your-key
SMTP_EMAIL=your-email
SMTP_PASSWORD=your-password
```

Then run:
```bash
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs` to explore all the endpoints.

---

## API Endpoints at a Glance

| Method | Route | What it does |
|---|---|---|
| POST | /auth/register | Create teacher account |
| POST | /auth/login | Login and get token |
| GET/POST | /classes | List or create classes |
| GET/POST | /students | List or add students |
| POST | /sessions | Create a class session |
| POST | /attendance | Mark bulk attendance |
| POST | /assessments | Create an assessment |
| POST | /grades | Save student marks |
| GET | /report/:id | Full student report |
| POST | /email/:id | Email parent |

---

## A Note on Security

Passwords are handled entirely by Supabase Auth. Every API request needs a JWT token. The database has row-level security so teachers are completely isolated from each other's data. Secret keys are stored as environment variables — never in the code.

---

Built by **Mr. Govind Gupta and Dr. Narendra Mohan** — Data Science Trainer at GLA University, Mathura  
*FDP on Agentic AI — June 2026*
