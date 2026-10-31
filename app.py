import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection, init_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "development-key-change-before-deployment")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    conn = get_db_connection()
    if q:
        jobs = conn.execute("""
            SELECT jobs.*, users.name AS employer_name
            FROM jobs JOIN users ON users.id = jobs.employer_id
            WHERE jobs.title LIKE ? OR jobs.company LIKE ? OR jobs.location LIKE ?
            ORDER BY jobs.created_at DESC
        """, (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
    else:
        jobs = conn.execute("""
            SELECT jobs.*, users.name AS employer_name
            FROM jobs JOIN users ON users.id = jobs.employer_id
            ORDER BY jobs.created_at DESC
        """).fetchall()
    conn.close()
    return render_template("index.html", jobs=jobs, q=q)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "seeker")
        if role not in ("seeker", "employer"):
            role = "seeker"
        if not name or not email or len(password) < 8:
            flash("Enter your name, a valid email, and a password of at least 8 characters.", "error")
            return render_template("register.html")
        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                (name, email, generate_password_hash(password), role)
            )
            conn.commit()
        except Exception:
            conn.close()
            flash("That email may already be registered. Please try another.", "error")
            return render_template("register.html")
        conn.close()
        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))
        flash("Incorrect email or password.", "error")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/jobs")
def jobs():
    return redirect(url_for("index", **request.args))


@app.route("/job/<int:job_id>")
def job_detail(job_id):
    conn = get_db_connection()
    job = conn.execute("""
        SELECT jobs.*, users.name AS employer_name, users.email AS employer_email
        FROM jobs JOIN users ON users.id = jobs.employer_id
        WHERE jobs.id = ?
    """, (job_id,)).fetchone()
    applied = False
    if job and session.get("role") == "seeker":
        applied = conn.execute(
            "SELECT id FROM applications WHERE job_id = ? AND seeker_id = ?",
            (job_id, session["user_id"])
        ).fetchone() is not None
    conn.close()
    if not job:
        abort(404)
    return render_template("job_detail.html", job=job, applied=applied)


@app.route("/apply/<int:job_id>", methods=["POST"])
@role_required("seeker")
def apply_job(job_id):
    cover_letter = request.form.get("cover_letter", "").strip()
    conn = get_db_connection()
    job = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        conn.close()
        abort(404)
    try:
        conn.execute(
            "INSERT INTO applications (job_id, seeker_id, cover_letter) VALUES (?, ?, ?)",
            (job_id, session["user_id"], cover_letter)
        )
        conn.commit()
        flash("Application submitted successfully!", "success")
    except Exception:
        flash("You have already applied for this job.", "warning")
    conn.close()
    return redirect(url_for("job_detail", job_id=job_id))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()
    if session["role"] == "employer":
        my_jobs = conn.execute(
            "SELECT * FROM jobs WHERE employer_id = ? ORDER BY created_at DESC",
            (session["user_id"],)
        ).fetchall()
        applications = conn.execute("""
            SELECT applications.*, jobs.title AS job_title, users.name AS applicant_name,
                   users.email AS applicant_email
            FROM applications
            JOIN jobs ON jobs.id = applications.job_id
            JOIN users ON users.id = applications.seeker_id
            WHERE jobs.employer_id = ?
            ORDER BY applications.applied_at DESC
        """, (session["user_id"],)).fetchall()
        conn.close()
        return render_template("dashboard.html", my_jobs=my_jobs, applications=applications)
    applications = conn.execute("""
        SELECT applications.*, jobs.title AS job_title, jobs.company, jobs.location
        FROM applications JOIN jobs ON jobs.id = applications.job_id
        WHERE applications.seeker_id = ?
        ORDER BY applications.applied_at DESC
    """, (session["user_id"],)).fetchall()
    conn.close()
    return render_template("dashboard.html", applications=applications, my_jobs=[])


@app.route("/post-job", methods=["GET", "POST"])
@role_required("employer")
def post_job():
    if request.method == "POST":
        fields = {key: request.form.get(key, "").strip() for key in
                  ("title", "company", "location", "job_type", "salary", "description", "requirements")}
        if not all(fields[key] for key in ("title", "company", "location", "job_type", "description")):
            flash("Please complete all required fields.", "error")
            return render_template("post_job.html", job=fields)
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO jobs (title, company, location, job_type, salary, description, requirements, employer_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (fields["title"], fields["company"], fields["location"], fields["job_type"],
              fields["salary"], fields["description"], fields["requirements"], session["user_id"]))
        conn.commit()
        conn.close()
        flash("Job posted successfully!", "success")
        return redirect(url_for("dashboard"))
    return render_template("post_job.html", job={})


@app.route("/edit-job/<int:job_id>", methods=["GET", "POST"])
@role_required("employer")
def edit_job(job_id):
    conn = get_db_connection()
    job = conn.execute("SELECT * FROM jobs WHERE id = ? AND employer_id = ?",
                       (job_id, session["user_id"])).fetchone()
    if not job:
        conn.close()
        abort(404)
    if request.method == "POST":
        fields = {key: request.form.get(key, "").strip() for key in
                  ("title", "company", "location", "job_type", "salary", "description", "requirements")}
        if not all(fields[key] for key in ("title", "company", "location", "job_type", "description")):
            flash("Please complete all required fields.", "error")
            conn.close()
            return render_template("post_job.html", job=fields, editing=True)
        conn.execute("""
            UPDATE jobs SET title=?, company=?, location=?, job_type=?, salary=?,
                description=?, requirements=? WHERE id=? AND employer_id=?
        """, (fields["title"], fields["company"], fields["location"], fields["job_type"],
              fields["salary"], fields["description"], fields["requirements"], job_id, session["user_id"]))
        conn.commit()
        conn.close()
        flash("Job updated successfully.", "success")
        return redirect(url_for("dashboard"))
    conn.close()
    return render_template("post_job.html", job=job, editing=True)


@app.route("/delete-job/<int:job_id>", methods=["POST"])
@role_required("employer")
def delete_job(job_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM jobs WHERE id = ? AND employer_id = ?", (job_id, session["user_id"]))
    conn.commit()
    conn.close()
    flash("Job deleted if it belonged to your account.", "success")
    return redirect(url_for("dashboard"))


@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="You do not have permission to view this page."), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="The page or job you requested was not found."), 404


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
