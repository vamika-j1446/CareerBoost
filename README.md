# CareerBoost – Resume & Job Readiness Analyzer

An AI-powered resume analyzer built with Flask and Groq AI (LLaMA 3.3).

## Features
- Resume scoring across 5 sections (Education, Skills, Projects, Experience, Certifications)
- ATS compatibility suggestions
- AI-generated personalized interview questions
- Job role recommendations based on resume
- Interview preparation (DSA, DBMS, OS, OOP, HR)
- Score history with graph
- Download analysis report as PDF
- User login and registration

## Tech Stack
- Frontend: HTML, CSS, JavaScript
- Backend: Python, Flask
- Database: MySQL
- AI: Groq API (LLaMA 3.3 70B)
- PDF: PyMuPDF, ReportLab

## How to Run
1. Clone the repo
2. Install dependencies: pip install flask python-dotenv pymupdf python-docx mysql-connector-python groq werkzeug reportlab
3. Create .env file with your GROQ_API_KEY
4. Setup MySQL database (see schema in README)
5. Run: python app.py
6. Open: http://127.0.0.1:5001
