import sqlite3
import os
from config import Config

def get_db():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    db_exists = os.path.exists(Config.DATABASE)
    conn = sqlite3.connect(Config.DATABASE)
    cursor = conn.cursor()
    
    tables = """
    CREATE TABLE IF NOT EXISTS village (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        taluk TEXT,
        district TEXT,
        state TEXT,
        population INTEGER,
        total_houses INTEGER,
        total_roads INTEGER,
        panchayat TEXT,
        ward TEXT,
        mp_name TEXT,
        mla_name TEXT,
        road_maintenance_officer TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS roads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        road_code TEXT UNIQUE NOT NULL,
        road_name TEXT NOT NULL,
        road_type TEXT,
        length_m INTEGER,
        width_m INTEGER,
        crosses TEXT,
        houses_start INTEGER,
        houses_end INTEGER,
        house_count INTEGER,
        qr_code_url TEXT,
        qr_image_path TEXT,
        latitude REAL,
        longitude REAL,
        health_score INTEGER DEFAULT 100,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS road_intersections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        road_id INTEGER,
        intersects_with_road_id INTEGER,
        FOREIGN KEY (road_id) REFERENCES roads(id),
        FOREIGN KEY (intersects_with_road_id) REFERENCES roads(id)
    );

    CREATE TABLE IF NOT EXISTS crosses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        road_id INTEGER,
        cross_name TEXT,
        cross_number INTEGER,
        latitude REAL,
        longitude REAL,
        FOREIGN KEY (road_id) REFERENCES roads(id)
    );

    CREATE TABLE IF NOT EXISTS houses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        house_number TEXT,
        road_id INTEGER,
        cross_id INTEGER,
        owner_name TEXT,
        mobile TEXT,
        FOREIGN KEY (road_id) REFERENCES roads(id),
        FOREIGN KEY (cross_id) REFERENCES crosses(id)
    );

    CREATE TABLE IF NOT EXISTS citizens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        mobile TEXT NOT NULL,
        email TEXT,
        address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id TEXT UNIQUE NOT NULL,
        citizen_id INTEGER,
        road_id INTEGER,
        cross_id INTEGER,
        village_name TEXT,
        road_code TEXT,
        road_name TEXT,
        cross_name TEXT,
        latitude REAL,
        longitude REAL,
        complaint_type TEXT,
        description TEXT,
        severity TEXT DEFAULT 'Medium',
        status TEXT DEFAULT 'Pending',
        citizen_name TEXT,
        citizen_mobile TEXT,
        date TEXT,
        time TEXT,
        admin_remark TEXT,
        resolved_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS complaint_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id INTEGER,
        image_path TEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (complaint_id) REFERENCES complaints(id)
    );

    CREATE TABLE IF NOT EXISTS complaint_votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id INTEGER,
        citizen_name TEXT,
        citizen_mobile TEXT,
        voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (complaint_id) REFERENCES complaints(id)
    );

    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT,
        role TEXT DEFAULT 'admin',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id INTEGER,
        message TEXT,
        sent_to TEXT,
        sent_via TEXT DEFAULT 'dashboard',
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (complaint_id) REFERENCES complaints(id)
    );

    CREATE TABLE IF NOT EXISTS road_maintenance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        road_id INTEGER,
        maintenance_type TEXT,
        description TEXT,
        cost REAL,
        start_date TEXT,
        end_date TEXT,
        status TEXT DEFAULT 'Planned',
        assigned_to TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (road_id) REFERENCES roads(id)
    );
    """
    
    for statement in tables.split(';'):
        statement = statement.strip()
        if statement:
            cursor.execute(statement)
    
    conn.commit()
    return conn, cursor

def populate_sample_data(conn, cursor):
    cursor.execute("SELECT COUNT(*) FROM village")
    if cursor.fetchone()[0] > 0:
        print("Sample data already exists.")
        return

    cursor.execute("""
        INSERT INTO village (name, taluk, district, state, population, total_houses, total_roads, panchayat, ward, mp_name, mla_name, road_maintenance_officer)
        VALUES ('Shantinagar', 'Ramanagara', 'Ramanagara', 'Karnataka', 1120, 245, 10, 'Shantinagar Gram Panchayat', '3', 'Shri Ramesh Gowda', 'Smt. Lakshmi Devi', 'Mr. Manjunath K.')
    """)

    roads_data = [
        ('R001', 'Main Road', 'Asphalt', 850, 7, 45, 1, 45, 12.9410, 77.4530, 92),
        ('R002', 'Temple Road', 'Concrete', 450, 5, 27, 46, 72, 12.9420, 77.4540, 80),
        ('R003', 'School Road', 'Asphalt', 600, 6, 33, 73, 105, 12.9405, 77.4520, 73),
        ('R004', 'Market Road', 'Concrete', 450, 5, 27, 106, 132, 12.9425, 77.4545, 65),
        ('R005', 'Lake View Road', 'Asphalt', 700, 6, 33, 133, 165, 12.9400, 77.4550, 45),
        ('R006', 'Hospital Road', 'Asphalt', 600, 6, 20, 166, 185, 12.9395, 77.4515, 70),
        ('R007', 'Bus Stand Road', 'Concrete', 500, 5, 20, 186, 205, 12.9430, 77.4548, 75),
        ('R008', 'Garden Road', 'Asphalt', 700, 5, 15, 206, 220, 12.9398, 77.4555, 85),
        ('R009', 'Canal Road', 'Gravel', 350, 4, 15, 221, 235, 12.9390, 77.4510, 30),
        ('R010', 'Extension Road', 'Concrete', 500, 5, 10, 236, 245, 12.9435, 77.4550, 88),
    ]
    
    road_ids = {}
    for r in roads_data:
        cursor.execute("""
            INSERT INTO roads (road_code, road_name, road_type, length_m, width_m, house_count, houses_start, houses_end, latitude, longitude, health_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, r)
        road_ids[r[0]] = cursor.lastrowid

    intersections = [
        ('R001', 'R002'), ('R001', 'R003'), ('R001', 'R005'),
        ('R002', 'R004'),
        ('R003', 'R006'),
        ('R004', 'R007'),
        ('R005', 'R008'),
        ('R006', 'R009'),
        ('R007', 'R010'),
    ]
    for a, b in intersections:
        cursor.execute("INSERT INTO road_intersections (road_id, intersects_with_road_id) VALUES (?, ?)", (road_ids[a], road_ids[b]))

    cross_data = {
        'R001': 5, 'R002': 3, 'R003': 4, 'R004': 3, 'R005': 4,
        'R006': 3, 'R007': 3, 'R008': 3, 'R009': 2, 'R010': 2,
    }
    cross_ids = {}
    for road_code, num_crosses in cross_data.items():
        for i in range(1, num_crosses + 1):
            cursor.execute("""
                INSERT INTO crosses (road_id, cross_name, cross_number, latitude, longitude)
                VALUES (?, ?, ?, ?, ?)
            """, (road_ids[road_code], f'Cross-{i}', i,
                  12.9400 + (abs(hash(road_code)) % 50) * 0.0001,
                  77.4530 + (abs(hash(road_code)) % 50) * 0.0001))
            cross_ids[f'{road_code}_C{i}'] = cursor.lastrowid

    sample_houses = []
    house_counter = 1
    for road_code in ['R001','R002','R003','R004','R005','R006','R007','R008','R009','R010']:
        r = [x for x in roads_data if x[0] == road_code][0]
        for h in range(r[6], r[7] + 1):
            cross_keys = [k for k in cross_ids if k.startswith(road_code)]
            cross_id = cross_ids[cross_keys[house_counter % len(cross_keys)]] if cross_keys else None
            sample_houses.append((f'H{h:03d}', road_ids[road_code], cross_id, f'Resident {h}', f'9876{h:06d}'))
            house_counter += 1

    for h in sample_houses[:50]:
        cursor.execute("INSERT INTO houses (house_number, road_id, cross_id, owner_name, mobile) VALUES (?, ?, ?, ?, ?)", h)

    sample_complaints = [
        ('C000001', None, road_ids['R001'], cross_ids.get('R001_C2'), 'Shantinagar', 'R001', 'Main Road', 'Cross-2', 12.9410, 77.4530, 'Pothole', 'Large pothole near House H015. Approximately 2 feet wide. Vehicles are getting damaged.', 'High', 'Pending', 'Ravi Kumar', '9876500015', '2026-06-10', '10:34:00'),
        ('C000002', None, road_ids['R002'], cross_ids.get('R002_C1'), 'Shantinagar', 'R002', 'Temple Road', 'Cross-1', 12.9420, 77.4540, 'Water Logging', 'Water logging near temple area after rain. Water is 1 foot deep.', 'Medium', 'In Progress', 'Priya S', '9876500060', '2026-06-12', '14:20:00'),
        ('C000003', None, road_ids['R003'], cross_ids.get('R003_C3'), 'Shantinagar', 'R003', 'School Road', 'Cross-3', 12.9405, 77.4520, 'Road Crack', 'Major crack running across the road near school gate.', 'Medium', 'Completed', 'Anil M', '9876500084', '2026-06-13', '09:15:00'),
        ('C000004', None, road_ids['R007'], cross_ids.get('R007_C2'), 'Shantinagar', 'R007', 'Bus Stand Road', 'Cross-2', 12.9430, 77.4548, 'Broken Drain', 'Drain cover is broken. Open drain is dangerous for children.', 'Critical', 'Pending', 'Suresh K', '9876500194', '2026-06-15', '16:45:00'),
        ('C000005', None, road_ids['R009'], cross_ids.get('R009_C1'), 'Shantinagar', 'R009', 'Canal Road', 'Cross-1', 12.9390, 77.4510, 'Damaged Road', 'Road edge is completely broken. Gravel road is deteriorating.', 'High', 'Pending', 'Kumar R', '9876500229', '2026-06-16', '11:00:00'),
        ('C000006', None, road_ids['R005'], cross_ids.get('R005_C2'), 'Shantinagar', 'R005', 'Lake View Road', 'Cross-2', 12.9400, 77.4550, 'Pothole', 'Multiple potholes on Lake View Road. Very dangerous for two-wheelers.', 'Critical', 'Pending', 'Deepa N', '9876500145', '2026-06-17', '08:30:00'),
        ('C000007', None, road_ids['R005'], cross_ids.get('R005_C1'), 'Shantinagar', 'R005', 'Lake View Road', 'Cross-1', 12.9401, 77.4551, 'Garbage', 'Garbage dumped on road side. Stinking and causing health issues.', 'Medium', 'In Progress', 'Ramesh P', '9876500133', '2026-06-18', '07:45:00'),
        ('C000008', None, road_ids['R004'], cross_ids.get('R004_C1'), 'Shantinagar', 'R004', 'Market Road', 'Cross-1', 12.9425, 77.4545, 'Street Light', 'Street lights not working for past 2 weeks. Market area is dark at night.', 'Low', 'Pending', 'Farmer John', '9876500110', '2026-06-19', '19:20:00'),
    ]

    for c in sample_complaints:
        cursor.execute("""
            INSERT INTO complaints (complaint_id, citizen_id, road_id, cross_id, village_name, road_code, road_name, cross_name, latitude, longitude, complaint_type, description, severity, status, citizen_name, citizen_mobile, date, time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, c)

    cursor.execute("""
        INSERT INTO admin_users (username, password, full_name, role)
        VALUES ('admin', 'admin123', 'Village Administrator', 'admin'),
               ('mla', 'mla123', 'Smt. Lakshmi Devi', 'mla'),
               ('engineer', 'eng123', 'Mr. Manjunath K.', 'engineer')
    """)

    conn.commit()
    print("Sample data populated successfully!")

if __name__ == '__main__':
    conn, cursor = init_database()
    populate_sample_data(conn, cursor)
    cursor.close()
    conn.close()
