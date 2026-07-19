import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Serverless /tmp workaround for SQLite and uploads
if os.environ.get('LAMBDA_TASK_ROOT') or os.environ.get('NETLIFY'):
    DATABASE_PATH = '/tmp/road_complaints.db'
    UPLOAD_PATH = '/tmp/static/uploads'
    QR_PATH = '/tmp/static/qr_codes'
    
    # Copy template database if not present in /tmp
    orig_db = os.path.join(BASE_DIR, 'road_complaints.db')
    if not os.path.exists(DATABASE_PATH) and os.path.exists(orig_db):
        shutil.copy2(orig_db, DATABASE_PATH)
        
    os.makedirs(UPLOAD_PATH, exist_ok=True)
    os.makedirs(QR_PATH, exist_ok=True)
else:
    DATABASE_PATH = os.path.join(BASE_DIR, 'road_complaints.db')
    UPLOAD_PATH = os.path.join(BASE_DIR, 'static', 'uploads')
    QR_PATH = os.path.join(BASE_DIR, 'static', 'qr_codes')

class Config:
    SECRET_KEY = 'road-complaint-system-secret-key-2026'
    DATABASE = DATABASE_PATH
    UPLOAD_FOLDER = UPLOAD_PATH
    QR_FOLDER = QR_PATH
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    VILLAGE_NAME = 'Shantinagar'
    DISTRICT = 'Ramanagara'
    STATE = 'Karnataka'
    MLA_NAME = 'Smt. Lakshmi Devi'
    MP_NAME = 'Shri Ramesh Gowda'
    PANCHAYAT = 'Shantinagar Gram Panchayat'
    BASE_URL = 'http://localhost:5000'

