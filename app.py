from flask import Flask, render_template, request, jsonify, session, redirect, url_for, make_response
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import os
import fitz
import json
import mysql.connector
from groq import Groq
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from io import BytesIO
import datetime

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
cursor = db.cursor(dictionary=True)

app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

# ── Interview Questions Bank ──────────────────────────────────
QUESTIONS = {
    "dsa": [
        {"q": "What is the difference between Array and Linked List?", "level": "easy", "a": "Arrays store elements in contiguous memory locations with O(1) access by index but O(n) insertion/deletion. Linked Lists store elements as nodes with pointers, offering O(1) insertion/deletion at head but O(n) access by index. Arrays are better for random access; Linked Lists for frequent insertions and deletions."},
        {"q": "Explain time and space complexity with examples.", "level": "easy", "a": "Time complexity measures how runtime grows with input size. Space complexity measures memory usage. Example: Linear search is O(n) time, O(1) space. Merge sort is O(n log n) time, O(n) space. Binary search is O(log n) time, O(1) space."},
        {"q": "What is a Stack and where is it used?", "level": "easy", "a": "A Stack is a LIFO (Last In First Out) data structure. Operations: push (add), pop (remove), peek (view top). Used in: function call management, undo operations in editors, balanced parentheses checking, browser back button, expression evaluation."},
        {"q": "What is a Queue and what are its types?", "level": "easy", "a": "A Queue is a FIFO (First In First Out) data structure. Types: Simple Queue, Circular Queue (rear connects to front), Priority Queue (elements served by priority), Double Ended Queue (deque — insert/delete from both ends). Used in: scheduling, BFS, print spooling."},
        {"q": "Explain Binary Search and its time complexity.", "level": "easy", "a": "Binary Search finds an element in a sorted array by repeatedly halving the search space. Compare target with middle element — if equal, found; if less, search left half; if greater, search right half. Time: O(log n). Space: O(1) iterative, O(log n) recursive."},
        {"q": "What is a Binary Search Tree (BST)?", "level": "medium", "a": "A BST is a binary tree where left child < parent < right child. Supports search, insert, delete in O(log n) average, O(n) worst case (skewed tree). Inorder traversal gives sorted output. Used in: dictionaries, dynamic sets, priority queues."},
        {"q": "What is the difference between BFS and DFS?", "level": "medium", "a": "BFS (Breadth First Search) explores level by level using a Queue — finds shortest path in unweighted graphs. DFS (Depth First Search) explores as far as possible using a Stack/recursion — used for cycle detection, topological sort, pathfinding. BFS: O(V+E) time, O(V) space. DFS: O(V+E) time, O(V) space."},
        {"q": "What is Dynamic Programming? Give an example.", "level": "medium", "a": "Dynamic Programming solves complex problems by breaking them into overlapping subproblems and storing results (memoization/tabulation) to avoid redundant computation. Example: Fibonacci — instead of recalculating fib(3) multiple times, store it. Other examples: Knapsack problem, Longest Common Subsequence, Matrix Chain Multiplication."},
        {"q": "Explain Merge Sort and why it is preferred over Bubble Sort.", "level": "medium", "a": "Merge Sort is a divide-and-conquer algorithm. Divide array into halves recursively, sort each, then merge. Time: O(n log n) best/average/worst. Space: O(n). Bubble Sort is O(n²) average/worst. Merge Sort is preferred for large datasets, is stable, and guarantees O(n log n). Bubble Sort is only useful for nearly sorted small arrays."},
        {"q": "What is a Hash Table and how does it handle collisions?", "level": "medium", "a": "A Hash Table stores key-value pairs using a hash function to map keys to indices. Average O(1) for insert/search/delete. Collision handling: Chaining (each bucket holds a linked list), Open Addressing (probe for next empty slot — linear, quadratic, double hashing). Load factor determines when to resize."},
        {"q": "What is a Heap and what are its types?", "level": "hard", "a": "A Heap is a complete binary tree satisfying the heap property. Min-Heap: parent ≤ children (root is minimum). Max-Heap: parent ≥ children (root is maximum). Used in: Priority Queue, Heap Sort (O(n log n)), finding kth largest/smallest element. Built in O(n) using heapify."},
        {"q": "Explain Dijkstra's algorithm.", "level": "hard", "a": "Dijkstra's finds shortest path from source to all vertices in a weighted graph with non-negative edges. Uses a Min-Heap priority queue. Start with source distance 0, all others infinity. Greedily pick minimum distance unvisited vertex, relax neighbors. Time: O((V+E) log V) with min-heap. Cannot handle negative edges."}
    ],
    "dbms": [
        {"q": "What is the difference between DDL, DML and DCL?", "level": "easy", "a": "DDL (Data Definition Language): defines structure — CREATE, ALTER, DROP, TRUNCATE. DML (Data Manipulation Language): manipulates data — SELECT, INSERT, UPDATE, DELETE. DCL (Data Control Language): controls access — GRANT, REVOKE. TCL (Transaction Control Language): manages transactions — COMMIT, ROLLBACK, SAVEPOINT."},
        {"q": "What is normalization? Explain 1NF, 2NF, 3NF.", "level": "medium", "a": "Normalization organizes tables to reduce redundancy. 1NF: each column has atomic values, no repeating groups. 2NF: 1NF + no partial dependency (non-key attributes depend on full primary key). 3NF: 2NF + no transitive dependency (non-key attributes don't depend on other non-key attributes). BCNF: stricter 3NF where every determinant is a candidate key."},
        {"q": "What is the difference between Primary Key and Foreign Key?", "level": "easy", "a": "Primary Key uniquely identifies each row in a table — cannot be NULL, only one per table. Foreign Key references the Primary Key of another table — establishes relationship between tables, can have multiple per table, can be NULL. Used to maintain referential integrity."},
        {"q": "What is a JOIN? Explain types.", "level": "medium", "a": "JOIN combines rows from two or more tables. INNER JOIN: rows matching in both tables. LEFT JOIN: all rows from left + matching from right (NULL if no match). RIGHT JOIN: all rows from right + matching from left. FULL OUTER JOIN: all rows from both tables. CROSS JOIN: cartesian product. SELF JOIN: join table with itself."},
        {"q": "What is an Index and why is it used?", "level": "medium", "a": "An Index is a data structure that speeds up data retrieval. Like a book index — instead of scanning all pages, go directly. Types: Clustered (physical order matches index — one per table), Non-clustered (logical order, multiple allowed). Trade-off: faster reads but slower writes, extra storage. Created on frequently queried columns."},
        {"q": "What is ACID in database transactions?", "level": "medium", "a": "ACID ensures reliable transactions. Atomicity: all operations succeed or all fail (no partial). Consistency: database moves from one valid state to another. Isolation: concurrent transactions don't interfere. Durability: committed transactions survive failures. Example: bank transfer — both debit and credit must succeed together."},
        {"q": "What is the difference between DELETE, TRUNCATE and DROP?", "level": "easy", "a": "DELETE: removes specific rows with WHERE clause, can be rolled back, triggers fire, slow for large data. TRUNCATE: removes all rows, cannot be rolled back (DDL), faster, resets identity. DROP: removes entire table including structure, cannot be rolled back. DELETE is DML; TRUNCATE and DROP are DDL."},
        {"q": "Write a SQL query to find the second highest salary.", "level": "hard", "a": "SELECT MAX(salary) FROM employees WHERE salary < (SELECT MAX(salary) FROM employees); OR using LIMIT: SELECT salary FROM employees ORDER BY salary DESC LIMIT 1 OFFSET 1; OR using DENSE_RANK: SELECT salary FROM (SELECT salary, DENSE_RANK() OVER (ORDER BY salary DESC) as rnk FROM employees) t WHERE rnk = 2;"}
    ],
    "os": [
        {"q": "What is a process vs a thread?", "level": "easy", "a": "A Process is an independent program in execution with its own memory space, PCB, and resources. A Thread is the smallest unit of execution within a process — threads share memory and resources of the parent process. Processes are isolated; threads communicate easily but risk race conditions. Context switching between threads is faster than between processes."},
        {"q": "What is deadlock? What are the four conditions?", "level": "medium", "a": "Deadlock is a state where processes wait for each other indefinitely. Four Coffman conditions: Mutual Exclusion (resource held by one process at a time), Hold and Wait (process holds a resource while waiting for another), No Preemption (resources cannot be forcibly taken), Circular Wait (circular chain of processes each waiting for next). All four must hold simultaneously."},
        {"q": "Explain CPU scheduling algorithms.", "level": "medium", "a": "FCFS: First Come First Served — simple, non-preemptive, convoy effect. SJF: Shortest Job First — optimal average waiting time, needs burst time prediction. Round Robin: each process gets a time quantum — fair, preemptive, good for time-sharing. Priority Scheduling: highest priority runs first — starvation possible. MLFQ: Multi-Level Feedback Queue — combines advantages of multiple algorithms."},
        {"q": "What is paging and segmentation?", "level": "medium", "a": "Paging: divides physical memory into fixed-size frames, logical memory into same-size pages. Eliminates external fragmentation but causes internal fragmentation. Uses page table for translation. Segmentation: divides memory into variable-size logical segments (code, data, stack). Matches programmer's view, causes external fragmentation. Segmentation with paging combines both approaches."},
        {"q": "What is a semaphore?", "level": "medium", "a": "A Semaphore is a synchronization tool — an integer variable accessed via two atomic operations: wait() (P) decrements, signal() (V) increments. Binary semaphore (mutex): 0 or 1 — mutual exclusion. Counting semaphore: any non-negative integer — resource counting. Solves producer-consumer, reader-writer, dining philosophers problems."},
        {"q": "What is virtual memory?", "level": "hard", "a": "Virtual memory allows processes to use more memory than physically available by storing parts on disk. Only active pages stay in RAM; inactive pages swap to disk (swap space). Benefits: run large programs, process isolation, efficient memory use. Page fault occurs when accessing a page not in RAM — OS fetches it. Managed using page replacement algorithms: FIFO, LRU, Optimal."}
    ],
    "oops": [
        {"q": "What are the four pillars of OOP?", "level": "easy", "a": "Encapsulation: bundling data and methods, hiding internal state (private/public). Abstraction: showing only essential features, hiding implementation (abstract classes, interfaces). Inheritance: a class acquires properties of another class — promotes reuse. Polymorphism: one interface, many implementations — method overloading (compile-time) and method overriding (runtime)."},
        {"q": "What is the difference between overloading and overriding?", "level": "easy", "a": "Method Overloading: same method name, different parameters in the same class — compile-time polymorphism. Example: add(int,int) and add(double,double). Method Overriding: subclass redefines parent method with same signature — runtime polymorphism. Requires inheritance. @Override annotation in Java helps catch errors."},
        {"q": "What is an abstract class vs interface?", "level": "medium", "a": "Abstract class: can have abstract and concrete methods, constructor, instance variables. A class can extend only one abstract class. Interface: only abstract methods (before Java 8), no constructor, no instance variables. A class can implement multiple interfaces. Use abstract class for shared base implementation; interface for capability contracts."},
        {"q": "What is the difference between == and .equals() in Java?", "level": "easy", "a": "== compares references (memory addresses) for objects, values for primitives. .equals() compares content/state of objects. Example: String a = new String('hello'); String b = new String('hello'); a == b is false (different objects), a.equals(b) is true (same content). Always use .equals() for String comparison."},
        {"q": "Explain the SOLID principles.", "level": "hard", "a": "S: Single Responsibility — one class, one reason to change. O: Open/Closed — open for extension, closed for modification. L: Liskov Substitution — subclass can replace parent without breaking code. I: Interface Segregation — don't force clients to implement unused methods. D: Dependency Inversion — depend on abstractions, not concrete implementations. These principles make code maintainable and scalable."},
        {"q": "What is a constructor? What are its types?", "level": "easy", "a": "A constructor initializes an object when it is created. Same name as class, no return type. Types: Default constructor (no parameters — provided by compiler if none defined), Parameterized constructor (takes arguments to initialize with specific values), Copy constructor (creates object from another object of same class). Constructors can be overloaded."}
    ],
    "hr": [
        {"q": "Tell me about yourself.", "level": "easy", "a": "Structure: Present-Past-Future. Present: current education, skills, what you're good at. Past: relevant projects, internships, achievements. Future: what you want to achieve, why this company. Keep it under 2 minutes. Be confident, specific, and connect your story to the role you're applying for."},
        {"q": "What are your strengths and weaknesses?", "level": "easy", "a": "Strengths: Pick 2-3 relevant to the role, give examples. E.g., 'I'm detail-oriented — in my project I caught a critical bug before deployment.' Weaknesses: Be honest but show self-awareness and improvement. E.g., 'I used to struggle with time management but I now use task prioritization tools and have improved significantly.'"},
        {"q": "Where do you see yourself in 5 years?", "level": "easy", "a": "Show ambition but align with the company. Example: 'In 5 years I see myself as a senior developer, leading projects and mentoring juniors. I want to grow technically and in leadership. I believe [company name]'s focus on [relevant area] aligns perfectly with where I want to grow.' Avoid: 'I want to start my own company soon.'"},
        {"q": "Why should we hire you?", "level": "medium", "a": "Connect your skills to their needs. Structure: 'I have [skill], proven by [example]. I can contribute to [specific thing they do]. I'm a quick learner and [one personal quality]. Among your candidates, I believe my [unique quality] makes me stand out.' Research the company before so you can be specific about what you bring."},
        {"q": "Tell me about a challenge you faced and how you handled it.", "level": "medium", "a": "Use the STAR method: Situation (context), Task (your role), Action (what you did specifically), Result (outcome). Example: 'During my project, our API kept timing out (S). I was responsible for the backend (T). I profiled the code, found a missing database index, and added it (A). Response time dropped from 4 seconds to 200ms (R).' Always end with a positive result."},
        {"q": "Do you have any questions for us?", "level": "easy", "a": "Always ask 2-3 questions — shows genuine interest. Good questions: 'What does success look like in this role in the first 6 months?', 'What are the biggest technical challenges the team is currently facing?', 'What does the onboarding/training process look like?', 'What do you enjoy most about working here?' Avoid asking about salary, leaves, or benefits in first round."}
    ]
}

# ── Text Extraction ───────────────────────────────────────────
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

# ── AI Analysis ───────────────────────────────────────────────
def analyze_resume_with_ai(resume_text):
    prompt = f"""
You are a strict, expert resume analyzer for campus placements and ATS systems. Analyze this resume honestly and thoroughly.

Resume:
{resume_text}

Score harshly and realistically:
- Only well-known certifications (AWS, Google, Microsoft, NPTEL, Coursera specializations) score above 70
- Projects without GitHub links, impact metrics, or tech stack details score below 60
- Experience section with no internships scores below 50
- Skills with only basic languages and no frameworks/tools score below 60

Give SPECIFIC suggestions — not generic ones. Mention actual things missing FROM THIS RESUME.
Also give ATS (Applicant Tracking System) improvement suggestions — things like keywords, formatting, file type, section headers.

Respond ONLY in this exact JSON format:
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
        {{"type": "<impressive/developing/needs_attention>", "text": "<specific suggestion referencing actual content of this resume>"}}
    ],
    "ats_suggestions": [
        "<specific ATS improvement suggestion 1>",
        "<specific ATS improvement suggestion 2>",
        "<specific ATS improvement suggestion 3>",
        "<specific ATS improvement suggestion 4>",
        "<specific ATS improvement suggestion 5>"
    ],
    "jobs": ["<job title 1>", "<job title 2>", "<job title 3>", "<job title 4>"],
    "interview_questions": [
        "<personalized question 1>",
        "<personalized question 2>",
        "<personalized question 3>",
        "<personalized question 4>",
        "<personalized question 5>",
        "<personalized question 6>",
        "<personalized question 7>",
        "<personalized question 8>"
    ]
}}

Rules:
- impressive = 75 and above
- developing = 50 to 74  
- needs_attention = below 50
- suggestions: be SPECIFIC — mention actual project names, skill names, certification names from the resume
- ats_suggestions: focus on ATS compatibility — keywords, formatting, section naming, file format, bullet points, fonts
- jobs: suggest 4 realistic job roles based on their actual skills
- interview_questions: specific to THIS person's resume — mention their actual project names and technologies
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    result = response.choices[0].message.content.strip()
    if result.startswith("```"):
        result = result.split("```")[1]
        if result.startswith("json"):
            result = result[4:]
    return result.strip()

# ── PDF Report Generator ──────────────────────────────────────
def generate_pdf_report(result, filename):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle('title', fontSize=24, fontName='Helvetica-Bold', textColor=colors.HexColor('#2E75B6'), spaceAfter=6)
    sub_style = ParagraphStyle('sub', fontSize=12, fontName='Helvetica', textColor=colors.grey, spaceAfter=20)
    heading_style = ParagraphStyle('heading', fontSize=14, fontName='Helvetica-Bold', textColor=colors.HexColor('#1a1a1a'), spaceBefore=16, spaceAfter=8)
    body_style = ParagraphStyle('body', fontSize=11, fontName='Helvetica', textColor=colors.HexColor('#333333'), spaceAfter=6, leading=16)

    elements.append(Paragraph("CareerBoost Analysis Report", title_style))
    elements.append(Paragraph(f"Resume: {filename} | Generated: {datetime.datetime.now().strftime('%d %b %Y, %I:%M %p')}", sub_style))
    elements.append(Spacer(1, 0.1*inch))

    elements.append(Paragraph(f"Overall Score: {result['overall']} / 100", heading_style))
    elements.append(Spacer(1, 0.1*inch))

    elements.append(Paragraph("Section Scores", heading_style))
    table_data = [['Section', 'Score', 'Status']]
    for sec in result['sections']:
        table_data.append([sec['name'], str(sec['score']), sec['status'].replace('_', ' ').title()])
    t = Table(table_data, colWidths=[200, 80, 150])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2E75B6')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 11),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f0f4ff'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.2*inch))

    elements.append(Paragraph("Suggestions for Improvement", heading_style))
    for i, sug in enumerate(result['suggestions'], 1):
        elements.append(Paragraph(f"{i}. {sug['text']}", body_style))

    if result.get('jobs'):
        elements.append(Paragraph("Recommended Job Roles", heading_style))
        for job in result['jobs']:
            elements.append(Paragraph(f"• {job}", body_style))

    if result.get('interview_questions'):
        elements.append(Paragraph("Your Personalized Interview Questions", heading_style))
        for i, q in enumerate(result['interview_questions'], 1):
            elements.append(Paragraph(f"Q{i}. {q}", body_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ── Routes ────────────────────────────────────────────────────
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        try:
            cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
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
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return redirect(url_for('dashboard'))
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

@app.route('/interview')
def interview():
    return render_template('interview.html', questions=QUESTIONS)

@app.route('/history')
def history():
    cursor.execute("""
        SELECT s.*, r.filename FROM scores s
        JOIN resumes r ON s.resume_id = r.id
        ORDER BY s.analyzed_at DESC LIMIT 20
    """)
    scores = cursor.fetchall()
    return render_template('history.html', scores=scores)

@app.route('/clear-history', methods=['POST'])
def clear_history():
    cursor.execute("DELETE FROM scores")
    cursor.execute("DELETE FROM resumes")
    db.commit()
    return redirect(url_for('history'))

@app.route('/delete-score/<int:score_id>', methods=['POST'])
def delete_score(score_id):
    cursor.execute("DELETE FROM scores WHERE id = %s", (score_id,))
    db.commit()
    return redirect(url_for('history'))

@app.route('/api/analyze', methods=['POST'])
def analyze():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ['pdf', 'docx']:
        return jsonify({'error': 'Only PDF and DOCX supported'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    cursor.execute("INSERT INTO resumes (filename) VALUES (%s)", (file.filename,))
    db.commit()
    resume_id = cursor.lastrowid

    resume_text = extract_text_from_pdf(filepath) if ext == 'pdf' else extract_text_from_docx(filepath)

    if len(resume_text.strip()) < 50:
        return jsonify({'error': 'Could not read file. Upload a text-based PDF or DOCX.'}), 400

    try:
        ai_result = analyze_resume_with_ai(resume_text)
        result = json.loads(ai_result)
    except Exception as e:
        return jsonify({'error': 'AI analysis failed. Please try again.'}), 500

    cursor.execute("""
        INSERT INTO scores (resume_id, overall_score, education_score, skills_score,
        projects_score, experience_score, certifications_score, suggestions)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        resume_id,
        result['overall'],
        result['sections'][0]['score'],
        result['sections'][1]['score'],
        result['sections'][2]['score'],
        result['sections'][3]['score'],
        result['sections'][4]['score'],
        json.dumps(result['suggestions'])
    ))
    db.commit()

    # Store result in session for PDF download
    session['last_result'] = result
    session['last_filename'] = file.filename

    return jsonify(result)

@app.route('/download-report')
def download_report():
    result = session.get('last_result')
    filename = session.get('last_filename', 'resume')
    if not result:
        return redirect(url_for('home'))
    buffer = generate_pdf_report(result, filename)
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=CareerBoost_Report_{filename}.pdf'
    return response

if __name__ == '__main__':
    app.run(debug=True, port=5001)