# CareerConnect — Online Job Portal

A responsive job portal built with Python, Flask, SQLite, HTML, CSS, and JavaScript.

## Features
- Job seeker and employer registration/login
- Secure password hashing
- Search jobs by title, company, or location
- Job details and application submission
- Seeker dashboard to track applications
- Employer dashboard to post, edit, and delete jobs
- Employer view of applications received
- Role-based access checks and responsive layout

## Requirements
- Python 3.10+
- pip

## Run locally (Windows PowerShell)
```powershell
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python database.py
python app.py
```
Open http://127.0.0.1:5000

## Notes
- Create an account and choose either “Find a job” or “Hire candidates / post jobs”.
- Employers can publish listings; job seekers can apply.
- Set a strong `SECRET_KEY` environment variable before deployment.
- SQLite is suitable for a learning project. For production deployment, use a persistent database service.
- This starter does not yet include email verification, password reset, resume uploads, application-status editing, or CSRF protection.

## Project structure
```text
online_job_portal/
├── app.py
├── database.py
├── requirements.txt
├── templates/
└── static/
    ├── css/style.css
    └── js/script.js
```
