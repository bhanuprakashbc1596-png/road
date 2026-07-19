import os
import qrcode
import sqlite3
from config import Config

os.makedirs(Config.QR_FOLDER, exist_ok=True)
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

conn = sqlite3.connect(Config.DATABASE)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT * FROM roads ORDER BY road_code")
roads = cursor.fetchall()

for road in roads:
    rc = road["road_code"]
    url = f"{Config.BASE_URL}/report?road={rc}"
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    filename = f"qr_{rc}.png"
    filepath = os.path.join(Config.QR_FOLDER, filename)
    img.save(filepath)
    cursor.execute("UPDATE roads SET qr_code_url=?, qr_image_path=? WHERE id=?", (url, filename, road["id"]))

conn.commit()
cursor.close()
conn.close()
print(f"Generated {len(roads)} QR codes!")
