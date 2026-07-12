from flask import Flask, render_template, request, redirect, session, send_from_directory
from flask_mysqldb import MySQL

import os
import json
import uuid

import config
from utils.pdf_reader import extract_text
from utils.text_preprocessing import clean_text
from utils.vectorizer import create_vectors
from utils.similarity import calculate_similarity
from utils.skill_match import compare_skills
from utils.recommendation import get_recommendation
from utils.ats_score import calculate_ats_score
from utils.suggestions import generate_suggestions
from utils.pdf_report import generate_pdf
from flask_mail import Mail, Message
import random
import nltk


nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('punkt_tab')


# Create Flask App
app = Flask(__name__)
app.secret_key = "resume_screening_secret_key"

UPLOAD_FOLDER = "uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Database Configuration
app.config["MYSQL_HOST"] = config.MYSQL_HOST
app.config["MYSQL_USER"] = config.MYSQL_USER
app.config["MYSQL_PASSWORD"] = config.MYSQL_PASSWORD
app.config["MYSQL_DB"] = config.MYSQL_DB

# Create MySQL Object
# Create MySQL Object
mysql = MySQL(app)
# ==========================
# Mail Configuration
# ==========================

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False

app.config["MAIL_USERNAME"] = "airesumescreening23@gmail.com"

# Gmail App Password (WITHOUT SPACES)
app.config["MAIL_PASSWORD"] = "wgvwwizgxfpgldad"

app.config["MAIL_DEFAULT_SENDER"] = (
    "AI Resume Screening",
    "airesumescreening23@gmail.com"
)

mail = Mail(app)
# Home Page


@app.route("/")
def home():
    return render_template("index.html")



# Login Page
@app.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        remember = request.form.get("remember")

        cursor = mysql.connection.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=%s",
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()

        if user and user[3] == password:

            session["user_id"] = user[0]
            session["user_name"] = user[1]

            if remember:
                session.permanent = True

            return redirect("/dashboard")

        error = "Invalid Email or Password"

    return render_template("login.html", error=error)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/send_forgot_otp", methods=["POST"])
def send_forgot_otp():

    data = request.get_json()

    email = data["email"]

    cursor = mysql.connection.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email=%s",
        (email,)
    )

    user = cursor.fetchone()

    cursor.close()

    if not user:

        return {
            "success": False,
            "message": "Email not registered."
        }

    otp = str(random.randint(100000,999999))

    session["forgot_otp"] = otp
    session["forgot_email"] = email

    msg = Message(
    subject="Forgot Password OTP",
    recipients=[email]
)

    msg.body = f"""
Hello,

Your Registration OTP is:

        {otp}

This OTP is valid for 5 minutes.

Please do not share it with anyone.

Regards,
AI Resume Screening Team
        """
    try:
        mail.send(msg)
        print("Forgot Password OTP Sent")

        return {
        "success": True,
        "message": "OTP Sent Successfully."
    }

    except Exception as e:
        print("Mail Error:", e)

    return {
        "success": False,
        "message": str(e)
    }


@app.route("/update_password", methods=["POST"])
def update_password():

    data = request.get_json()

    otp = data["otp"]
    password = data["password"]
    confirm = data["confirm"]

    if otp != session.get("forgot_otp"):

        return {
            "success": False,
            "message": "Invalid OTP."
        }

    if password != confirm:

        return {
            "success": False,
            "message": "Passwords do not match."
        }

    cursor = mysql.connection.cursor()

    cursor.execute(
        """
        UPDATE users
        SET password=%s
        WHERE email=%s
        """,
        (
            password,
            session["forgot_email"]
        )
    )

    mysql.connection.commit()

    cursor.close()

    session.pop("forgot_otp",None)
    session.pop("forgot_email",None)

    return {
        "success": True,
        "message": "Password Updated Successfully."
    }
@app.route("/forgot_password")
def forgot_password():

    return render_template("forgot_password.html")



@app.route("/verify_forgot_otp", methods=["POST"])
def verify_forgot_otp():

    data = request.get_json()

    otp = data["otp"]

    if otp == session.get("forgot_otp"):

        session["otp_verified"] = True

        return {
            "success": True,
            "message": "OTP Verified Successfully"
        }

    return {
        "success": False,
        "message": "Invalid OTP"
    }



@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT 
            COUNT(*),
            IFNULL(AVG(ats_score), 0),
            IFNULL(MAX(ats_score), 0)
        FROM resume_analysis_full
        WHERE user_id=%s
    """, (session["user_id"],))

    stats = cursor.fetchone() or (0, 0, 0)

    cursor.execute("""
        SELECT ats_score, file_name
        FROM resume_analysis_full
        WHERE user_id=%s
        ORDER BY created_at DESC
        LIMIT 1
    """, (session["user_id"],))

    latest = cursor.fetchone()

    cursor.close()

    return render_template(
        "dashboard.html",
        total=stats[0],
        avg_ats=round(stats[1], 2),
        best_ats=stats[2],
        latest=latest
    )

@app.route("/analyze_resume", methods=["POST"])
def analyze_resume():

    if "user_id" not in session:
        return redirect("/login")

    job_description = request.form["job_description"]

    resume = request.files["resume"]

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        resume.filename
    )

    resume.save(file_path)

    resume_text = extract_text(file_path)

    cleaned_resume = clean_text(resume_text)

    cleaned_job = clean_text(job_description)



    print("========== CLEANED RESUME ==========")
    print(cleaned_resume)

    print("\n========== CLEANED JOB ==========")
    print(cleaned_job)
            




    vectors = create_vectors(cleaned_resume, cleaned_job)

# TF-IDF Similarity Score
    tfidf_score = calculate_similarity(vectors)

# Skill Matching
    comparison, matched = compare_skills(
    cleaned_resume,
    cleaned_job
)
    
    missing_skills, suggestions = generate_suggestions(
    comparison,
    resume_text
)

    total_skills = len(comparison)

    if total_skills > 0:

        ats = calculate_ats_score(
        comparison,
        resume_text
    )

    else:

        ats = {
        "technical": 0,
        "education": 0,
        "experience": 0,
        "projects": 0,
        "certification": 0,
        "total": 0
    }

    ats_score = ats["total"]
# Recommendation based on ATS Score
    recommendation = get_recommendation(ats_score)
    
    cursor = mysql.connection.cursor()

    query = """
INSERT INTO resume_analysis_full
(user_id, file_name, job_description,
tfidf_score, ats_score, recommendation,
missing_skills, suggestions, comparison)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
"""

    cursor.execute(query, (
    session["user_id"],
    resume.filename,
    job_description,
    round(tfidf_score, 2),
    ats_score,
    recommendation["status"],

    json.dumps(missing_skills),
    json.dumps(suggestions),
    json.dumps(comparison)
))

    mysql.connection.commit()
    cursor.close()


    print("\n========== TF-IDF SCORE ==========")
    print(tfidf_score)

    print("\n========== ATS SCORE ==========")
    print(ats_score)
    
    
    # store result in session
    session["process"] = {
    "ats": ats,
    "missing_skills": missing_skills,
    "suggestions": suggestions,
    "file_name": resume.filename,
    "file_size": round(os.path.getsize(file_path)/1024,2),
    "characters": len(resume_text),
    "resume_text": resume_text,
    "cleaned_resume": cleaned_resume,
    "job_description": job_description,
    "cleaned_job": cleaned_job,
    "resume_words": len(resume_text.split()),
    "cleaned_words": len(cleaned_resume.split()),
    "job_words": len(job_description.split()),
    "cleaned_job_words": len(cleaned_job.split()),
    "comparison": comparison,
    "tfidf_score": round(tfidf_score,2),
    "ats_score": ats_score,
    "recommendation": recommendation
}
    session["last_job_description"] = job_description
    session["process_ready"] = True

# IMPORTANT: redirect to dashboard
    return redirect("/dashboard")


@app.route("/process")
def process():

    if "process" not in session:
        return redirect("/dashboard")

    session["process_ready"] = False  # hide button after view

    return render_template("process.html", process=session["process"])

@app.route("/view_resume/<filename>")
def view_resume(filename):

    if "user_id" not in session:
        return redirect("/login")

    return send_from_directory("uploads", filename)
@app.route("/test_mail")
def test_mail():
    try:
        msg = Message(
        subject="Test Email",
        recipients=["mpravin23mp@gmail.com"]
    )

        msg.body = "Hello from Render"

        mail.send(msg)

        return "Mail Sent Successfully"
    except Exception:
        import traceback
        return f"<pre>{traceback.format_exc()}</pre>"

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form["full_name"]
        email = request.form["email"]
        password = request.form["password"]
        confirm = request.form["confirm"]

        if password != confirm:

            return render_template(
                "register.html",
                error="Passwords do not match!"
            )

        if not session.get("register_verified"):

            return render_template(
                "register.html",
                error="Please verify your OTP first."
            )

        cursor = mysql.connection.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=%s",
            (email,)
        )

        user = cursor.fetchone()

        if user:

            cursor.close()

            return render_template(
                "register.html",
                error="Email already exists!"
            )

        cursor.execute(
            """
            INSERT INTO users(full_name,email,password)
            VALUES(%s,%s,%s)
            """,
            (
                full_name,
                email,
                password
            )
        )

        mysql.connection.commit()
        cursor.close()

        # Send Welcome Email
        msg = Message(
    subject="Welcome to AI Resume Screening System",
    recipients=[email]
)

        msg.body = f"""
Hi {full_name},

Welcome to AI Resume Screening System.

Your account has been created successfully.

You can now login and start analyzing your resume.

Thank you for registering.

Regards,
AI Resume Screening Team
"""

        try:
            mail.send(msg)
            print("Mail Sent Successfully")
        except Exception as e:
            print("Mail Error:", e)

        session.pop("register_otp", None)
        session.pop("register_email", None)
        session.pop("register_verified", None)

        return redirect("/login")

    return render_template("register.html")



@app.route("/send_register_otp", methods=["POST"])
def send_register_otp():

    print("========== SEND REGISTER OTP ==========")

    data = request.get_json()
    print("Received Data:", data)

    email = data["email"]

    cursor = mysql.connection.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email=%s",
        (email,)
    )

    user = cursor.fetchone()
    cursor.close()

    if user:
        return {
            "success": False,
            "message": "Email already registered."
        }

    otp = str(random.randint(100000, 999999))

    session["register_otp"] = otp
    session["register_email"] = email

    print("Generated OTP:", otp)

    msg = Message(
        subject="Registration OTP",
        recipients=[email]
    )

    msg.body = f"""
Hi,

Your Registration OTP is:

{otp}

Do not share this OTP with anyone.

AI Resume Screening System
"""

    try:
        print("Sending email to:", email)
        mail.send(msg)
        print("Email sent successfully!")

        return {
            "success": True,
            "message": "OTP Sent Successfully."
        }

    except Exception as e:
        import traceback
        traceback.print_exc()

        return {
            "success": False,
            "message": str(e)
        }
    
    
@app.route("/verify_register_otp", methods=["POST"])
def verify_register_otp():

    data = request.get_json()

    otp = data["otp"]

    if otp == session.get("register_otp"):

        session["register_verified"] = True

        return {
            "success": True,
            "message": "OTP Verified Successfully."
        }

    return {
        "success": False,
        "message": "Invalid OTP."
    }

@app.route("/history")
def history():

    if "user_id" not in session:
        return redirect("/login")

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT 
            id,
            file_name,
            job_description,
            tfidf_score,
            ats_score,
            recommendation,
            missing_skills,
            suggestions,
            comparison,
            created_at
        FROM resume_analysis_full
        WHERE user_id=%s
        ORDER BY created_at DESC
    """, (session["user_id"],))

    rows = cursor.fetchall()
    cursor.close()

    formatted_history = []

    for row in rows:

        formatted_history.append({
            "id": row[0],
            "file_name": row[1],
            "job_description": row[2],
            "tfidf_score": row[3],
            "ats_score": row[4],
            "recommendation": row[5],

            "missing_skills": json.loads(row[6]) if row[6] else [],
            "suggestions": json.loads(row[7]) if row[7] else [],
            "comparison": json.loads(row[8]) if row[8] else [],

            "created_at": row[9]
        })

    return render_template("history.html", history=formatted_history)

@app.route("/delete_history/<int:id>")
def delete_history(id):

    if "user_id" not in session:
        return redirect("/login")

    cursor = mysql.connection.cursor()

    cursor.execute("""
        DELETE FROM resume_analysis_full
        WHERE id=%s AND user_id=%s
    """, (id, session["user_id"]))

    mysql.connection.commit()
    cursor.close()

    return redirect("/history")

@app.route("/download_report")
def download_report():

    if "process" not in session:
        return "No report found"

    filename = f"report_{uuid.uuid4().hex}.pdf"
    file_path = os.path.join("static", filename)

    generate_pdf(file_path, session["process"])

    return send_from_directory("static", filename, as_attachment=True)

@app.route("/rankings")
def rankings():

    if "user_id" not in session:
        return redirect("/login")

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT 
            u.full_name,
            r.file_name,
            r.ats_score,
            r.created_at
        FROM resume_analysis_full r
        JOIN users u ON u.id = r.user_id
        ORDER BY r.ats_score DESC
        LIMIT 10
    """)

    data = cursor.fetchall()
    cursor.close()

    return render_template("rankings.html", data=data)

@app.route("/admin", methods=["GET", "POST"])
def admin():

    error = None

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        cursor = mysql.connection.cursor()

        cursor.execute(
            "SELECT * FROM admin WHERE username=%s AND password=%s",
            (username, password)
        )

        admin = cursor.fetchone()

        cursor.close()

        if admin:

            session["admin"] = admin[0]

            return redirect("/admin-dashboard")

        error = "Invalid Username or Password"

    return render_template(
        "admin-login.html",
        error=error
    )



@app.route("/admin-dashboard")
def admin_dashboard():

    if "admin" not in session:
        return redirect("/admin")

    cursor = mysql.connection.cursor()

    # Total Users
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    # Active Users
    cursor.execute("SELECT COUNT(*) FROM users WHERE status='Active'")
    active_users = cursor.fetchone()[0]

    # Inactive Users
    cursor.execute("SELECT COUNT(*) FROM users WHERE status='Inactive'")
    inactive_users = cursor.fetchone()[0]

    # Total Resume Records
    cursor.execute("SELECT COUNT(*) FROM resume_analysis_full")
    total_records = cursor.fetchone()[0]

    cursor.close()

    return render_template(
        "admin-dashboard.html",
        total_users=total_users,
        active_users=active_users,
        inactive_users=inactive_users,
        total_records=total_records
    )



@app.route("/admin-users")
def admin_users():

    if "admin" not in session:
        return redirect("/admin")

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT id,
            full_name,
            email,
            status
        FROM users
    """)

    users = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin-users.html",
        users=users
    )



@app.route("/admin-records")
def admin_records():

    if "admin" not in session:
        return redirect("/admin")

    cursor = mysql.connection.cursor()

    cursor.execute("""
SELECT
resume_analysis_full.id,
users.full_name,
resume_analysis_full.file_name,
resume_analysis_full.ats_score,
resume_analysis_full.created_at
FROM resume_analysis_full
JOIN users
ON users.id=resume_analysis_full.user_id
ORDER BY created_at DESC
""")

    records = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin-records.html",
        records=records
    )

@app.route("/delete-record/<int:id>")
def delete_record(id):

    if "admin" not in session:
        return redirect("/admin")

    cursor = mysql.connection.cursor()

    cursor.execute("""
        DELETE FROM resume_analysis_full
        WHERE id=%s
    """, (id,))

    mysql.connection.commit()
    cursor.close()

    return redirect("/admin-records")

@app.route("/admin-logout")
def admin_logout():

    session.pop("admin", None)

    return redirect("/admin")


@app.route("/admin-view-resume/<filename>")
def admin_view_resume(filename):

    if "admin" not in session:
        return redirect("/admin")

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )

@app.route("/admin-rankings")
def admin_rankings():

    if "admin" not in session:
        return redirect("/admin")

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            u.full_name,
            r.file_name,
            r.ats_score,
            r.created_at
        FROM resume_analysis_full r
        JOIN users u
        ON u.id = r.user_id
        ORDER BY r.ats_score DESC
    """)

    data = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin-rankings.html",
        data=data
    )


@app.route("/admin-ranking-view/<filename>")
def admin_ranking_view(filename):

    if "admin" not in session:
        return redirect("/admin")

    return send_from_directory("uploads", filename)


@app.route("/activate-user/<int:id>")
def activate_user(id):

    if "admin" not in session:
        return redirect("/admin")

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE users
        SET status='Active'
        WHERE id=%s
    """, (id,))

    mysql.connection.commit()
    cursor.close()

    return redirect("/admin-users")


@app.route("/deactivate-user/<int:id>")
def deactivate_user(id):

    if "admin" not in session:
        return redirect("/admin")

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE users
        SET status='Inactive'
        WHERE id=%s
    """, (id,))

    mysql.connection.commit()
    cursor.close()

    return redirect("/admin-users")


@app.route("/delete-user/<int:id>")
def delete_user(id):

    if "admin" not in session:
        return redirect("/admin")

    cursor = mysql.connection.cursor()

    # Delete user's resume records first
    cursor.execute("""
        DELETE FROM resume_analysis_full
        WHERE user_id=%s
    """, (id,))

    # Delete user
    cursor.execute("""
        DELETE FROM users
        WHERE id=%s
    """, (id,))

    mysql.connection.commit()
    cursor.close()

    return redirect("/admin-users")


if __name__ == "__main__":
    app.run(debug=True)