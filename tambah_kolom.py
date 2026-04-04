import sqlite3

NAMA_DATABASE = 'database.db' 

def update_db():
    try:
        conn = sqlite3.connect(NAMA_DATABASE)
        cursor = conn.cursor()
        
        # Perintah untuk nambahin kolom reset_token
        cursor.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
        
        conn.commit()
        print("✅ Mantap! Kolom 'reset_token' berhasil ditambahkan.")
        conn.close()
    except sqlite3.OperationalError:
        print("⚠️ Kolom sepertinya sudah ada atau nama tabel 'users' salah.")
    except Exception as e:
        print(f"❌ Ada error: {e}")

if __name__ == "__main__":
    update_db()