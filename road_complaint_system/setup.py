"""
Road Complaint Management System - Quick Setup Script
Run this to initialize the database and generate QR codes.
"""
import subprocess
import sys
import os

def install_dependencies():
    print("[1/3] Installing dependencies...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])

def init_database():
    print("[2/3] Initializing database with sample data...")
    from init_db import init_database, populate_sample_data
    conn, cursor = init_database()
    populate_sample_data(conn, cursor)
    cursor.close()
    conn.close()

def generate_qr():
    print("[3/3] Generating QR codes...")
    os.makedirs('static/qr_codes', exist_ok=True)
    os.makedirs('static/uploads', exist_ok=True)
    import qrcode
    from config import Config
    import mysql.connector

    conn = mysql.connector.connect(
        host=Config.MYSQL_HOST, user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD, database=Config.MYSQL_DB
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM roads ORDER BY road_code")
    roads = cursor.fetchall()
    qr_folder = Config.QR_FOLDER
    for road in roads:
        url = f"{Config.BASE_URL}/report?road={road['road_code']}"
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        filename = f"qr_{road['road_code']}.png"
        img.save(os.path.join(qr_folder, filename))
        cursor.execute("UPDATE roads SET qr_code_url=%s, qr_image_path=%s WHERE id=%s", (url, filename, road['id']))
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Generated {len(roads)} QR codes in {qr_folder}")

if __name__ == '__main__':
    install_dependencies()
    init_database()
    generate_qr()
    print("\n========================================")
    print("Setup Complete!")
    print("Run: python app.py")
    print("Open: http://localhost:5000")
    print("Admin: http://localhost:5000/admin")
    print("Credentials: admin / admin123")
    print("========================================")
