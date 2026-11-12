
from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

app = Flask(__name__)
load_dotenv()

app.permanent_session_lifetime = timedelta(days=365)

app.secret_key = os.getenv("SECRET_KEY")

print("DB Password Loaded:", bool(os.getenv("DB_PASSWORD")))

# MySQL Database Connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password=os.getenv("DB_PASSWORD"),
    database="careeriq"
)

print("MySQL Database Connected Successfully!")


@app.route("/")
def home():
    return render_template("index.html")



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        cursor = db.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT id, name, email, password_hash FROM users WHERE email = %s",
                (email,)
            )
            user = cursor.fetchone()

            if user and check_password_hash(user["password_hash"], password):
                session.permanent = True
                
                session["user_id"] = user["id"]
                session["user_email"] = user["email"]
                session["user_name"] = user["name"]

                cursor.execute(
                    "SELECT id FROM students WHERE email = %s LIMIT 1",
                    (email,)
                    )
                existing_profile = cursor.fetchone()
                if existing_profile:
                    return redirect("/dashboard")
                else:
                    return redirect("/profile")

            flash("Invalid email or password. Please try again.")
            return redirect("/login")

        except mysql.connector.Error:
            flash("Unable to log in right now. Please try again.")
            return redirect("/login")

        finally:
            cursor.close()

    return render_template("login.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password or not confirm_password:
            flash("Please fill in all required fields.")
            return redirect("/register")

        if len(password) < 8:
            flash("Password must be at least 8 characters long.")
            return redirect("/register")

        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect("/register")

        cursor = db.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT id FROM users WHERE email = %s",
                (email,)
            )
            existing_user = cursor.fetchone()

            if existing_user:
                flash("An account with this email already exists. Please log in.")
                return redirect("/login")

            password_hash = generate_password_hash(password)

            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (%s, %s, %s)
                """,
                (name, email, password_hash)
            )

            new_user_id = cursor.lastrowid
            db.commit()

            session.permanent = True
            session["user_id"] = new_user_id
            session["user_email"] = email
            session["user_name"] = name

            flash("Account created successfully! Please complete your profile.")
            return redirect("/profile")

        except mysql.connector.Error:
            db.rollback()
            flash("Unable to create account. Please try again.")
            return redirect("/register")

        finally:
            cursor.close()

    return render_template("register.html")



@app.route("/dashboard")
def dashboard():
    if "user_email" not in session:
        return redirect("/login")

    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT name, email, college, degree, academic_year,
                   graduation_year, cgpa, skills, interests,
                   certifications, projects, career_goal, desired_career
            FROM students
            WHERE email = %s
            LIMIT 1
        """, (session["user_email"],))

        student = cursor.fetchone()

        # Default dashboard values
        profile_completion = 0
        skills_assessed = 0
        placement_activities = 0

        if student:
            # Calculate profile completion
            core_fields = [
                "name",
                "email",
                "college",
                "degree",
                "academic_year",
                "graduation_year",
                "skills",
                "interests"
            ]

            completed_fields = sum(
                1 for field in core_fields
                if student.get(field) not in (None, "")
            )

            profile_completion = round(
                (completed_fields / len(core_fields)) * 100
            )

            # Skill assessment tracking will be implemented later
            skills_assessed = 0

            # Placement activity tracking will be implemented later
            placement_activities = 0

        return render_template(
            "dashboard.html",
            profile_completion=profile_completion,
            student=student,
            skills_assessed=skills_assessed,
            placement_activities=placement_activities
        )

    finally:
        cursor.close()


@app.route("/analytics")
def analytics():

    if "user_email" not in session:
        return redirect("/login")

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT name, email, college, degree, academic_year,
               graduation_year, skills, interests,
               certifications, projects, career_goal,
               desired_career
        FROM students
        WHERE email = %s
        LIMIT 1
    """, (session["user_email"],))

    student = cursor.fetchone()
    cursor.close()

    core_fields = [
        "name",
        "email",
        "college",
        "degree",
        "academic_year",
        "graduation_year",
        "skills",
        "interests"
    ]

    if student:

        completed_fields = sum(
            1 for field in core_fields
            if student.get(field) not in (None, "")
        )

        profile_completion = round(
            (completed_fields / len(core_fields)) * 100
        )

        skill_count = len([
            s for s in (student.get("skills") or "").split(",")
            if s.strip()
        ])

        project_count = len([
            p for p in (student.get("projects") or "").split(",")
            if p.strip()
        ])

        certification_count = len([
            c for c in (student.get("certifications") or "").split(",")
            if c.strip()
        ])

    else:
        profile_completion = 0
        skill_count = 0
        project_count = 0
        certification_count = 0

    return render_template(
        "analytics.html",
        student=student,
        profile_completion=profile_completion,
        skill_count=skill_count,
        project_count=project_count,
        certification_count=certification_count
    )


@app.route("/readiness")
def readiness():

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT name, cgpa, skills, projects, certifications,
               academic_year, desired_career
        FROM students
        ORDER BY id DESC
        LIMIT 1
    """)

    student = cursor.fetchone()
    cursor.close()

    # Default values
    readiness_score = 0

    skills_score = 0
    projects_score = 0
    certifications_score = 0
    career_score = 0

    if student:

        # Technical Skills - 40 marks
        if student.get("skills"):
            skills = student["skills"].strip()
            skill_count = len(
                [s for s in skills.split(",") if s.strip()]
            )

            skills_score = min(skill_count * 5, 40)

        # Projects - 30 marks
        if student.get("projects"):
            projects = student["projects"].strip()
            project_count = len(
                [p for p in projects.split(",") if p.strip()]
            )

            projects_score = min(project_count * 15, 30)

        # Certifications - 20 marks
        if student.get("certifications"):
            certifications = student["certifications"].strip()
            certification_count = len(
                [c for c in certifications.split(",") if c.strip()]
            )

            certifications_score = min(
                certification_count * 10, 20
            )

        # Career Direction - 10 marks
        if student.get("desired_career"):
            career_score = 10

    # Total Readiness Score
    readiness_score = round(
        skills_score
        + projects_score
        + certifications_score
        + career_score
    )

    # Readiness Level
    if readiness_score >= 80:
        readiness_level = "Excellent"

    elif readiness_score >= 60:
        readiness_level = "Good"

    elif readiness_score >= 40:
        readiness_level = "Moderate"

    else:
        readiness_level = "Needs Improvement"

    return render_template(
        "readiness.html",
        student=student,
        readiness_score=readiness_score,
        readiness_level=readiness_level,
        skills_score=skills_score,
        projects_score=projects_score,
        certifications_score=certifications_score,
        career_score=career_score
    )

# ============================================================
# MODULE 4 - AI CAREER RECOMMENDATION
# ============================================================

@app.route("/career-recommendation")
def career_recommendation():

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT name, degree, academic_year, cgpa,
               skills, interests, certifications,
               projects, career_goal, desired_career
        FROM students
        ORDER BY id DESC
        LIMIT 1
    """)

    student = cursor.fetchone()
    cursor.close()


    # ========================================================
    # CAREER PROFILES
    # ========================================================

    career_profiles = {

        "Data Analyst": {

            "skills": [
                "python",
                "sql",
                "excel",
                "pandas",
                "numpy",
                "statistics",
                "power bi",
                "tableau",
                "data visualization"
            ],

            "interests": [
                "data",
                "analytics",
                "analysis",
                "numbers",
                "statistics",
                "business"
            ]
        },


        "Data Scientist": {

            "skills": [
                "python",
                "sql",
                "pandas",
                "numpy",
                "statistics",
                "machine learning",
                "scikit-learn",
                "data visualization"
            ],

            "interests": [
                "data",
                "analytics",
                "statistics",
                "machine learning",
                "research",
                "mathematics"
            ]
        },


        "AI/ML Engineer": {

            "skills": [
                "python",
                "numpy",
                "pandas",
                "machine learning",
                "deep learning",
                "scikit-learn",
                "tensorflow",
                "pytorch",
                "mathematics"
            ],

            "interests": [
                "artificial intelligence",
                "ai",
                "machine learning",
                "deep learning",
                "robotics",
                "technology"
            ]
        },


        "Software Developer": {

            "skills": [
                "python",
                "java",
                "c++",
                "c",
                "javascript",
                "data structures",
                "algorithms",
                "git",
                "programming"
            ],

            "interests": [
                "programming",
                "software",
                "technology",
                "problem solving",
                "applications",
                "coding"
            ]
        },


        "Web Developer": {

            "skills": [
                "html",
                "css",
                "javascript",
                "react",
                "node.js",
                "python",
                "flask",
                "php",
                "git"
            ],

            "interests": [
                "web",
                "website",
                "design",
                "frontend",
                "backend",
                "technology"
            ]
        },


        "Cyber Security Analyst": {

            "skills": [
                "networking",
                "linux",
                "python",
                "cyber security",
                "cybersecurity",
                "ethical hacking",
                "penetration testing",
                "cryptography",
                "firewalls",
                "wireshark"
            ],

            "interests": [
                "cyber security",
                "cybersecurity",
                "security",
                "ethical hacking",
                "networking",
                "privacy",
                "technology"
            ]
        },


        "Cloud & DevOps Engineer": {

            "skills": [
                "aws",
                "azure",
                "google cloud",
                "cloud computing",
                "linux",
                "docker",
                "kubernetes",
                "git",
                "jenkins",
                "devops",
                "networking"
            ],

            "interests": [
                "cloud",
                "cloud computing",
                "aws",
                "devops",
                "infrastructure",
                "technology",
                "automation"
            ]
        },


        "Database Administrator / Data Engineer": {

            "skills": [
                "sql",
                "mysql",
                "postgresql",
                "oracle",
                "database",
                "database management",
                "python",
                "pandas",
                "etl",
                "data engineering"
            ],

            "interests": [
                "database",
                "data",
                "data engineering",
                "sql",
                "analytics",
                "technology"
            ]
        }

    }


    recommendations = []


    # ========================================================
    # NO STUDENT PROFILE
    # ========================================================

    if not student:

        return render_template(
            "career_recommendation.html",
            student=None,
            recommendations=[]
        )


    # ========================================================
    # PREPARE STUDENT SKILLS
    # ========================================================

    student_skills = set()

    if student.get("skills"):

        student_skills = {
            skill.strip().lower()
            for skill in student["skills"].split(",")
            if skill.strip()
        }


    # ========================================================
    # PREPARE STUDENT INTERESTS
    # ========================================================

    student_interests = set()

    if student.get("interests"):

        student_interests = {
            interest.strip().lower()
            for interest in student["interests"].split(",")
            if interest.strip()
        }


    # ========================================================
    # CALCULATE CAREER MATCH
    # ========================================================

    for career, profile in career_profiles.items():

        career_skills = set(profile["skills"])

        career_interests = set(profile["interests"])


        # Matching skills

        matching_skills = (
            student_skills.intersection(career_skills)
        )


        # Matching interests

        matching_interests = (
            student_interests.intersection(career_interests)
        )


        # Missing skills

        missing_skills = (
            career_skills - student_skills
        )


        # ----------------------------------------------------
        # SKILL SCORE - 70%
        # ----------------------------------------------------

        if career_skills:

            skill_score = (
                len(matching_skills)
                / len(career_skills)
            ) * 70

        else:

            skill_score = 0


        # ----------------------------------------------------
        # INTEREST SCORE - 30%
        # ----------------------------------------------------

        if career_interests:

            interest_score = (
                len(matching_interests)
                / len(career_interests)
            ) * 30

        else:

            interest_score = 0


        # Final match score

        match_score = round(
            skill_score + interest_score
        )


        # ====================================================
        # LOW INFORMATION STUDENT
        # ====================================================

        total_information = (
            len(student_skills)
            + len(student_interests)
        )


        if total_information == 0:

            status = "Explore"

            match_score = None

        else:

            status = "Match"


        # ====================================================
        # ADD RECOMMENDATION
        # ====================================================

        recommendations.append({

            "career": career,

            "score": match_score,

            "status": status,

            "matching_skills": sorted(
                matching_skills
            ),

            "missing_skills": sorted(
                missing_skills
            )[:5],

            "matching_interests": sorted(
                matching_interests
            )

        })


    # ========================================================
    # SORT CAREERS
    # ========================================================

    recommendations.sort(

        key=lambda x:
            x["score"]
            if x["score"] is not None
            else -1,

        reverse=True
    )


    # ========================================================
    # SEND DATA TO HTML
    # ========================================================

    return render_template(

        "career_recommendation.html",

        student=student,

        recommendations=recommendations

    )

# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_email" not in session:
        return redirect("/login")

    email = session["user_email"]
    cursor = db.cursor(dictionary=True)

    try:
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            college = request.form.get("college", "").strip() or None
            degree = request.form.get("degree", "").strip() or None
            academic_year = request.form.get("academic_year", "").strip() or None
            graduation_year = request.form.get("graduation_year", "").strip() or None
            cgpa = request.form.get("cgpa", "").strip() or None
            skills = request.form.get("skills", "").strip() or None
            interests = request.form.get("interests", "").strip() or None
            certifications = request.form.get("certifications", "").strip() or None
            projects = request.form.get("projects", "").strip() or None
            career_goal = request.form.get("career_goal") or None
            desired_career = request.form.get("desired_career", "").strip() or None

            cursor.execute(
                "SELECT id FROM students WHERE email = %s LIMIT 1",
                (email,)
            )
            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE students
                    SET name=%s, college=%s, degree=%s,
                        academic_year=%s, graduation_year=%s, cgpa=%s,
                        skills=%s, interests=%s, certifications=%s,
                        projects=%s, career_goal=%s, desired_career=%s
                    WHERE id=%s
                """, (
                    name, college, degree, academic_year,
                    graduation_year, cgpa, skills, interests,
                    certifications, projects, career_goal,
                    desired_career, existing["id"]
                ))
            else:
                cursor.execute("""
                    INSERT INTO students (
                        name, email, college, degree, academic_year,
                        graduation_year, cgpa, skills, interests,
                        certifications, projects, career_goal, desired_career
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    name, email, college, degree, academic_year,
                    graduation_year, cgpa, skills, interests,
                    certifications, projects, career_goal, desired_career
                ))

            db.commit()
            flash("Profile saved successfully!")
            return redirect("/dashboard")

        cursor.execute(
            "SELECT * FROM students WHERE email = %s LIMIT 1",
            (email,)
        )
        student = cursor.fetchone()

        return render_template("profile.html", student=student)

    except mysql.connector.Error:
        db.rollback()
        flash("Unable to save or load your profile. Please try again.")
        return redirect("/dashboard")

    finally:
        cursor.close()


@app.route("/view-profile")
def view_profile():
    if "user_email" not in session:
        return redirect("/login")

    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM students WHERE email = %s LIMIT 1",
            (session["user_email"],)
        )
        student = cursor.fetchone()

        if not student:
            flash("Please complete your profile first.")
            return redirect("/profile")

        return render_template("view_profile.html", student=student)

    finally:
        cursor.close()


@app.route("/resume-intelligence")
def resume_intelligence():
    if "user_email" not in session:
        return redirect("/login")

    return render_template("resume_intelligence.html")


if __name__ == "__main__":
    app.run(debug=True)