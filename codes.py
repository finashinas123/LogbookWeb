from flask import Flask, render_template, request, redirect, url_for, flash, Response, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from weasyprint import HTML
from pathlib import Path
import base64
from datetime import datetime

# ------------------ APP SETUP ------------------ #
app = Flask(__name__)
app.secret_key = "supersecretkey"

basedir = Path(__file__).resolve().parent

# ------------------ DB SETUP ------------------ #
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{basedir / 'logbook.db'}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# ------------------ LOGIN ------------------ #
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ------------------ MODELS ------------------ #
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    form_type = db.Column(db.String(50))
    filename = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ------------------ INIT DB ------------------ #
with app.app_context():
    db.create_all()

    if not User.query.filter_by(username="admin").first():
        admin_pw = bcrypt.generate_password_hash("admin123").decode("utf-8")
        db.session.add(User(username="admin", password=admin_pw, role="admin"))
        db.session.commit()

# ------------------ USER LOADER ------------------ #
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------ PDF FOLDER ------------------ #
PDF_ROOT = basedir / "generated_pdfs"
PDF_ROOT.mkdir(exist_ok=True)

# ------------------ BASE64 IMAGES ------------------ #
def encode(path):
    return base64.b64encode(open(path, "rb").read()).decode()

logo_base64 = encode(basedir / "static/images/logo.png")
bg_base64 = encode(basedir / "static/images/opaclogo.png")
sign_base64 = encode(basedir / "static/images/sign.png")

# ------------------ HOME ------------------ #
@app.route('/')
def home():
    return redirect(url_for('login'))

# ------------------ LOGIN ------------------ #
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()

        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            login_user(user)

            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("clinician_dashboard"))

        flash("Invalid login", "danger")

    return render_template("login.html")

# ------------------ LOGOUT ------------------ #
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ------------------ ADMIN DASHBOARD ------------------ #
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    users = User.query.all()

    stats = {
        "total_users": User.query.count(),
        "total_reports": Report.query.count(),
        "cpbs": Report.query.filter_by(form_type="cpbs").count(),
        "ecmo": Report.query.filter_by(form_type="ecmo").count()
    }

    return render_template(
        "admin_dashboard.html",
        users=users,
        stats=stats
    )

# ------------------ ADD USER ------------------ #
@app.route('/admin/add_user', methods=['POST'])
@login_required
def add_user():
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    username = request.form['username']
    password = request.form['password']
    role = request.form['role']

    if User.query.filter_by(username=username).first():
        flash("User already exists", "warning")
        return redirect(url_for('admin_dashboard'))

    hashed = bcrypt.generate_password_hash(password).decode("utf-8")

    db.session.add(User(username=username, password=hashed, role=role))
    db.session.commit()

    return redirect(url_for('admin_dashboard'))

# ------------------ DELETE USER ------------------ #
@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    user = User.query.get(user_id)

    if user:
        if user.id == current_user.id:
            flash("You cannot delete yourself", "danger")
            return redirect(url_for('admin_dashboard'))

        db.session.delete(user)
        db.session.commit()

    return redirect(url_for('admin_dashboard'))

# ------------------ VIEW USER PDFS ------------------ #
@app.route('/admin/user_pdfs/<username>')
@login_required
def view_user_pdfs(username):
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    folder = PDF_ROOT / username
    pdfs = []

    if folder.exists():
        for file in folder.rglob("*.pdf"):
            pdfs.append({
                "name": file.name,
                "path": str(file.relative_to(PDF_ROOT))
            })

    return render_template("user_pdfs.html", username=username, pdfs=pdfs)

# ------------------ ADMIN REPORTS ------------------ #
@app.route('/admin/reports')
@login_required
def admin_reports():
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    reports = Report.query.order_by(Report.created_at.desc()).all()
    return render_template("admin_reports.html", reports=reports)

# ------------------ DOWNLOAD ------------------ #
@app.route('/download/<path:filepath>')
@login_required
def download_pdf(filepath):
    return send_from_directory(PDF_ROOT, filepath, as_attachment=True)

# ------------------ CLINICIAN ------------------ #
@app.route('/clinician/dashboard')
@login_required
def clinician_dashboard():
    if current_user.role != 'clinician':
        return redirect(url_for('login'))
    return render_template("clinician_dashboard.html")

# ------------------ PDF GENERATION ------------------ #
def generate_pdf(template, data, folder_name):
    folder = PDF_ROOT / current_user.username / folder_name
    folder.mkdir(parents=True, exist_ok=True)

    filename = folder / f"{data.get('procedure','procedure')}_{datetime.now().date()}.pdf"

    html = render_template(
        template,
        data=data,
        logo_base64=logo_base64,
        bg_base64=bg_base64,
        sign_base64=sign_base64
    )

    pdf = HTML(string=html).write_pdf()

    with open(filename, "wb") as f:
        f.write(pdf)

    # SAVE RELATIVE PATH
    rel_path = filename.relative_to(PDF_ROOT)

    db.session.add(Report(
        username=current_user.username,
        form_type=folder_name,
        filename=str(rel_path)
    ))
    db.session.commit()

    return filename, pdf

# ------------------ CPBS ------------------ #
@app.route('/clinician/cpbs', methods=['GET', 'POST'])
@login_required
def cpbs():
    if request.method == 'POST':
        data = request.form.to_dict()
        filename, pdf = generate_pdf("pdf1.html", data, "cpbs")

        return Response(pdf, mimetype='application/pdf',
                        headers={"Content-Disposition": f"attachment;filename={filename.name}"})

    return render_template("form.html")

# ------------------ ECMO ------------------ #
@app.route('/clinician/ecmo', methods=['GET', 'POST'])
@login_required
def ecmo():
    if request.method == 'POST':
        data = request.form.to_dict()
        filename, pdf = generate_pdf("pdf2.html", data, "ecmo")

        return Response(pdf, mimetype='application/pdf',
                        headers={"Content-Disposition": f"attachment;filename={filename.name}"})

    return render_template("form2.html")

# ------------------ RUN ------------------ #
if __name__ == "__main__":
    app.run(debug=True, port=5002)