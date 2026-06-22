from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import os
import fitz
import json
import mysql.connector
from groq import Groq

try:
    import docx
except ImportError:
    docx = None

load_dotenv()

client = Groq(api_key=os.getenv('GROQ_API_KEY'))

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'careerboost-secret-2024')

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="vamika@123",
    database="careerboost"
)
cursor = db.cursor()

app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024


def extract_text_from_pdf(filepath):
    text = ''
    doc = fitz.open(filepath)
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def extract_text_from_docx(filepath):
    if docx is None:
        return ''
    doc = docx.Document(filepath)
    return '\n'.join([para.text for para in doc.paragraphs])


def analyze_resume_with_ai(resume_text):
    prompt = f"""
You are an expert resume analyzer. Analyze the following resume and provide scores.

Resume:
{resume_text}

Give scores out of 100 for each section and provide ALL improvement suggestions you find.
Respond in this EXACT JSON format, nothing else:

{{
    "overall": <number>,
    "sections": [
        {{"name": "Education", "score": <number>, "status": "<impressive/developing/needs_attention>"}},
        {{"name": "Skills", "score": <number>, "status": "<impressive/developing/needs_attention>"}},
        {{"name": "Projects", "score": <number>, "status": "<impressive/developing/needs_attention>"}},
        {{"name": "Experience", "score": <number>, "status": "<impressive/developing/needs_attention>"}},
        {{"name": "Certifications", "score": <number>, "status": "<impressive/developing/needs_attention>"}}
    ],
    "suggestions": [
        {{"type": "<impressive/developing/needs_attention>", "text": "<suggestion>"}}
    ]
}}

Rules:
- impressive = score 75 and above
- developing = score 50 to 74
- needs_attention = score below 50
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    result = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if result.startswith("```"):
        result = result.split("```")[1]
        if result.startswith("json"):
            result = result[4:]
    return result.strip()


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/analyze', methods=['POST'])
def analyze():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ['pdf', 'docx']:
        return jsonify({'error': 'Only PDF and DOCX files are supported'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    # Insert into resumes table (user_id = NULL for now, login comes later)
    cursor.execute(
        "INSERT INTO resumes (filename) VALUES (%s)",
        (file.filename,)
    )
    db.commit()
    resume_id = cursor.lastrowid

    # Extract text based on file type
    if ext == 'pdf':
        resume_text = extract_text_from_pdf(filepath)
    else:
        resume_text = extract_text_from_docx(filepath)

    if len(resume_text.strip()) < 50:
        return jsonify({'error': 'Could not read file. Please upload a text-based PDF or DOCX.'}), 400

    # AI Analysis
    ai_result = analyze_resume_with_ai(resume_text)

    try:
        result = json.loads(ai_result)
    except json.JSONDecodeError:
        return jsonify({'error': 'AI returned unexpected format. Try again.'}), 500

    # Save scores to DB
    cursor.execute(
        """
        INSERT INTO scores (
            resume_id, overall_score, education_score,
            skills_score, projects_score, experience_score,
            certifications_score, suggestions
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            resume_id,
            result['overall'],
            result['sections'][0]['score'],
            result['sections'][1]['score'],
            result['sections'][2]['score'],
            result['sections'][3]['score'],
            result['sections'][4]['score'],
            json.dumps(result['suggestions'])
        )
    )
    db.commit()

    return jsonify(result)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        # Hash the password before saving
        hashed_password = generate_password_hash(password)
        
        try:
            cursor.execute(
                "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                (name, email, hashed_password)
            )
            db.commit()
            return redirect(url_for('login'))
        except:
            return render_template('register.html', error="Email already exists!")
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid email or password!")
    
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', name=session['user_name'])


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True, port=5001)