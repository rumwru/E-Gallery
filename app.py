import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from PIL import Image as PILImage # Rename agar tidak bentrok dengan model Image

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app = Flask(__name__)
app.secret_key = "secretkey"

# --- KONFIGURASI DATABASE (Disatukan ke satu file agar tidak bingung) ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gallery.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Folder upload
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- MODEL DATABASE (Semua pakai SQLAlchemy agar rapi) ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class ImageModel(db.Model):
    __tablename__ = 'images' # Kita beri nama images agar konsisten
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), nullable=False) # Kita simpan username pemiliknya
    is_favorite = db.Column(db.Boolean, default=False)

# --- ROUTES ---

@app.route("/", methods=["GET"])
def home():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template("auth.html")

@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username")
    password = request.form.get("password")

    if not username or not password:
        flash("Field tidak boleh kosong")
        return redirect(url_for("home"))

    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password=hashed_password)

    try:
        db.session.add(new_user)
        db.session.commit()
        flash("Akun berhasil dibuat, silakan login")
    except:
        db.session.rollback()
        flash("Username sudah digunakan")

    return redirect(url_for("home"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session["user"] = username
            return redirect(url_for("dashboard"))
        else:
            flash("Username atau password salah")
            return redirect(url_for("login"))

    return render_template("auth.html")

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    username = session['user']
    category = request.args.get('category', 'all')

    if category == 'favorite':
        images = ImageModel.query.filter_by(username=username, is_favorite=True).all()
    elif category == 'recent':
        images = ImageModel.query.filter_by(username=username).order_by(ImageModel.id.desc()).all()
    else:
        images = ImageModel.query.filter_by(username=username).all()

    return render_template('dashboard.html', user=username, images=images, category=category)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload', methods=['POST'])
def upload():
    if 'user' not in session: return redirect(url_for('login'))

    # Ambil list file (untuk multiple upload)
    files = request.files.getlist('photo')

    if not files or files[0].filename == '':
        flash("Pilih foto terlebih dahulu!")
        return redirect(request.url)

    for file in files:
        if file and allowed_file(file.filename):
            random_hex = secrets.token_hex(8)
            _, f_ext = os.path.splitext(file.filename)
            filename = random_hex + f_ext
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            try:
                # Proses Kompresi
                img = PILImage.open(file)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(filepath, "JPEG", optimize=True, quality=60)
            except Exception as e:
                # Jika gagal kompres (format aneh), simpan asli
                file.seek(0)
                file.save(filepath)

            # Simpan ke Database
            new_img = ImageModel(filename=filename, username=session['user'])
            db.session.add(new_img)
        else:
            flash(f"File {file.filename} ditolak (Format tidak didukung!)")

    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route("/delete/<int:id>")
def delete_image(id):
    if 'user' not in session: return redirect(url_for('login'))
    img = ImageModel.query.get(id)
    if img and img.username == session['user']:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], img.filename)
        if os.path.exists(file_path): os.remove(file_path)
        db.session.delete(img)
        db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/favorite/<int:id>")
def favorite_image(id):
    if 'user' not in session: return redirect(url_for('login'))
    img = ImageModel.query.get(id)
    if img and img.username == session['user']:
        img.is_favorite = not img.is_favorite
        db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username')
        token = secrets.token_hex(16)
        # Ganti URL ini sesuai alamat PythonAnywhere kamu jika ingin linknya bekerja
        link_reset = f"{request.host_url}reset/{token}"

        return f'''
            <div style="text-align:center; padding:50px; font-family:Arial;">
                <h3>Link Reset untuk {username}:</h3>
                <a href="{link_reset}" style="color:blue;">{link_reset}</a>
                <p>Klik link di atas untuk ganti password!</p>
            </div>
        '''
    return render_template('forgot_password.html')

@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        target_username = request.form.get('username')
        new_pass = request.form.get('password')

        user = User.query.filter_by(username=target_username).first()
        if user:
            user.password = generate_password_hash(new_pass)
            db.session.commit()
            flash("Password berhasil diperbarui untuk " + target_username)
            return redirect(url_for('login'))
        else:
            flash("Username tidak ditemukan!")

    return render_template('reset_password.html', token=token)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- INISIALISASI DATABASE ---
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)