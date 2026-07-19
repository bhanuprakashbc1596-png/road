import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = 'road-complaint-system-secret-key-2026'
    DATABASE = os.path.join(BASE_DIR, 'road_complaints.db')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    QR_FOLDER = os.path.join(BASE_DIR, 'static', 'qr_codes')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    VILLAGE_NAME = 'Shantinagar'
    DISTRICT = 'Ramanagara'
    STATE = 'Karnataka'
    MLA_NAME = 'Smt. Lakshmi Devi'
    MP_NAME = 'Shri Ramesh Gowda'
    PANCHAYAT = 'Shantinagar Gram Panchayat'
    BASE_URL = 'http://localhost:5000'
