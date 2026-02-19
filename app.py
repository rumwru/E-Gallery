import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "secretkey")

# --- KONFIGURASI DATABASE ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gallery.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Folder upload
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- MODEL DATABASE (HANYA SATU) ---
class Image(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    user_owner = db.Column(db.String(50), nullable=False)
    is_favorite = db.Column(db.Boolean, default=False)

# --- FUNGSI DATABASE SQLITE (UNTUK LOGIN/REGIS) ---
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

# --- ROUTES ---

@app.route("/", methods=["GET"])
def home():
    return render_template("auth.html")

@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username")
    password = request.form.get("password")
    if not username or not password:
        flash("Field tidak boleh kosong")
        return redirect(url_for("home"))
    
    hashed_password = generate_password_hash(password)
    try:
        conn = get_db()
        conn.execute("INSERT INTO users (username, password) VALUES (?,?)", (username, hashed_password))
        conn.commit()
        conn.close()
        flash("Akun berhasil dibuat, silakan login")
    except sqlite3.IntegrityError:
        flash("Username sudah digunakan")
    return redirect(url_for("home"))

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()

    if user and check_password_hash(user["password"], password):
        session["user"] = username
        return redirect(url_for("dashboard"))
    else:
        flash("Username atau password salah")
        return redirect(url_for("home"))

@app.route("/dashboard")
def dashboard():
    if "user" in session:
        # Menampilkan semua gambar (untuk tes)
        user_images = Image.query.all() 
        return render_template("dashboard.html", user=session["user"], images=user_images)
    return redirect(url_for("home"))

@app.route("/upload", methods=["POST"])
def upload():
    if "user" not in session: 
        return redirect(url_for("home"))
    
    file = request.files.get('photo')
    if file and file.filename != '':
        print(f"DEBUG: Sedang menyimpan {file.filename}")
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        # SIMPAN KE DATABASE (Wajib ada baris ini!)
        new_img = Image(filename=filename, user_owner=session['user'])
        db.session.add(new_img)
        db.session.commit()
        
        flash("Foto berhasil diunggah!")
    return redirect(url_for("dashboard"))

@app.route("/delete/<int:id>")
def delete_image(id):
    img = Image.query.get(id)
    if img:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], img.filename)
        if os.path.exists(file_path): os.remove(file_path)
        db.session.delete(img)
        db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/favorite/<int:id>")
def favorite_image(id):
    img = Image.query.get(id)
    if img:
        img.is_favorite = not img.is_favorite
        db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))
init_db()
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    # Render butuh port dinamis, kalau di lokal default ke 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


