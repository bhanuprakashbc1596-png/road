import os
import uuid
import qrcode
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import sqlite3
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov'}

def get_db():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_complaint_id():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM complaints")
    count = cursor.fetchone()[0] + 1
    cursor.close()
    conn.close()
    return f"C{count:06d}"

def get_road_stats(cursor, road_id):
    stats = {}
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE road_id = ?", (road_id,))
    stats['total_complaints'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE road_id = ? AND status = 'Pending'", (road_id,))
    stats['pending'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE road_id = ? AND status = 'In Progress'", (road_id,))
    stats['in_progress'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE road_id = ? AND status = 'Completed'", (road_id,))
    stats['completed'] = cursor.fetchone()[0]
    return stats

# ==================== CITIZEN ROUTES ====================

@app.route('/')
def index():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM village LIMIT 1")
    village = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) as total FROM complaints")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) as pending FROM complaints WHERE status='Pending'")
    pending = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) as completed FROM complaints WHERE status='Completed'")
    completed = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return render_template('index.html', village=village, total=total, pending=pending, completed=completed)

@app.route('/report')
def report_form():
    road_code = request.args.get('road', '')
    cross = request.args.get('cross', '')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM roads WHERE road_code = ?", (road_code,))
    road = cursor.fetchone()
    if road:
        cursor.execute("SELECT * FROM crosses WHERE road_id = ? ORDER BY cross_number", (road['id'],))
        crosses = cursor.fetchall()
    else:
        crosses = []
    cursor.execute("SELECT * FROM village LIMIT 1")
    village = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('report.html', road=road, crosses=crosses, village=village, preselected_cross=cross)

@app.route('/report/submit', methods=['POST'])
def submit_complaint():
    road_code = request.form.get('road_code', '')
    cross_id = request.form.get('cross_id', '')
    citizen_name = request.form.get('citizen_name', '').strip()
    citizen_mobile = request.form.get('citizen_mobile', '').strip()
    complaint_type = request.form.get('complaint_type', '')
    description = request.form.get('description', '').strip()
    latitude = request.form.get('latitude', '')
    longitude = request.form.get('longitude', '')
    severity = request.form.get('severity', 'Medium')

    if not citizen_name or not citizen_mobile or not complaint_type or not description:
        flash('Please fill all required fields.', 'danger')
        return redirect(url_for('report_form', road=road_code))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM roads WHERE road_code = ?", (road_code,))
    road = cursor.fetchone()
    if not road:
        flash('Invalid road.', 'danger')
        return redirect(url_for('index'))

    cross_name = ''
    if cross_id:
        cursor.execute("SELECT * FROM crosses WHERE id = ?", (int(cross_id),))
        cross = cursor.fetchone()
        if cross:
            cross_name = cross['cross_name']

    complaint_id = generate_complaint_id()
    cursor.execute("""
        INSERT INTO complaints (complaint_id, road_id, cross_id, village_name, road_code, road_name, cross_name, latitude, longitude, complaint_type, description, severity, status, citizen_name, citizen_mobile, date, time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?, ?, ?, ?)
    """, (complaint_id, road['id'], int(cross_id) if cross_id else None, 'Shantinagar', road_code, road['road_name'], cross_name,
          float(latitude) if latitude else road['latitude'],
          float(longitude) if longitude else road['longitude'],
          complaint_type, description, severity, citizen_name, citizen_mobile,
          date.today().strftime('%Y-%m-%d'), datetime.now().strftime('%H:%M:%S')))
    
    complaint_db_id = cursor.lastrowid

    files = request.files.getlist('photos')
    for f in files:
        if f and f.filename and allowed_file(f.filename):
            ext = f.filename.rsplit('.', 1)[1].lower()
            filename = f"{complaint_id}_{uuid.uuid4().hex[:8]}.{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            f.save(filepath)
            cursor.execute("INSERT INTO complaint_images (complaint_id, image_path) VALUES (?, ?)", (complaint_db_id, filename))

    cursor.execute("""
        INSERT INTO notifications (complaint_id, message, sent_to, sent_via)
        VALUES (?, ?, ?, 'dashboard')
    """, (complaint_db_id, f'New {complaint_type} complaint on {road["road_name"]} - {complaint_id}', 'MLA / Admin'))

    conn.commit()
    cursor.close()
    conn.close()

    return render_template('success.html', complaint_id=complaint_id, road_name=road['road_name'], cross_name=cross_name)

@app.route('/track')
def track():
    return render_template('track.html')

@app.route('/track/result', methods=['POST'])
def track_result():
    complaint_id = request.form.get('complaint_id', '').strip()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, r.latitude as road_lat, r.longitude as road_lon, r.health_score
        FROM complaints c
        LEFT JOIN roads r ON c.road_id = r.id
        WHERE c.complaint_id = ?
    """, (complaint_id,))
    complaint = cursor.fetchone()
    images = []
    if complaint:
        cursor.execute("SELECT * FROM complaint_images WHERE complaint_id = ?", (complaint['id'],))
        images = cursor.fetchall()
    cursor.close()
    conn.close()
    if not complaint:
        flash('Complaint not found. Please check your Complaint ID.', 'warning')
        return redirect(url_for('track'))
    return render_template('track_result.html', complaint=complaint, images=images)

# ==================== ADMIN ROUTES ====================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin_users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            session['admin'] = {'id': user['id'], 'username': user['username'], 'role': user['role'], 'name': user['full_name']}
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials.', 'danger')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/admin')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM complaints")
    total_complaints = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'")
    pending = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='In Progress'")
    in_progress = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Completed'")
    completed = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM roads")
    total_roads = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(length_m) FROM roads")
    total_length = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT r.road_code, r.road_name, r.length_m, r.health_score,
               COUNT(c.id) as complaint_count,
               SUM(CASE WHEN c.status='Pending' THEN 1 ELSE 0 END) as pending_count,
               SUM(CASE WHEN c.status='In Progress' THEN 1 ELSE 0 END) as progress_count,
               SUM(CASE WHEN c.status='Completed' THEN 1 ELSE 0 END) as completed_count
        FROM roads r
        LEFT JOIN complaints c ON r.id = c.road_id
        GROUP BY r.id
        ORDER BY complaint_count DESC
    """)
    road_stats = cursor.fetchall()

    cursor.execute("""
        SELECT r.road_name, cr.cross_name, COUNT(c.id) as complaint_count
        FROM complaints c
        JOIN crosses cr ON c.cross_id = cr.id
        JOIN roads r ON c.road_id = r.id
        GROUP BY r.road_name, cr.cross_name
        ORDER BY complaint_count DESC
    """)
    cross_stats = cursor.fetchall()

    cursor.execute("""
        SELECT complaint_type, COUNT(*) as count
        FROM complaints
        GROUP BY complaint_type
        ORDER BY count DESC
    """)
    complaint_types = cursor.fetchall()

    cursor.execute("""
        SELECT date as d, COUNT(*) as count
        FROM complaints
        GROUP BY date
        ORDER BY d DESC
        LIMIT 7
    """)
    daily_trends = cursor.fetchall()

    cursor.execute("""
        SELECT severity, COUNT(*) as count
        FROM complaints
        GROUP BY severity
    """)
    severity_stats = cursor.fetchall()

    cursor.execute("""
        SELECT * FROM complaints
        ORDER BY id DESC
        LIMIT 10
    """)
    recent_complaints = cursor.fetchall()

    cursor.execute("SELECT * FROM village LIMIT 1")
    village = cursor.fetchone()

    cursor.execute("""
        SELECT r.road_name, r.health_score
        FROM roads r
        ORDER BY r.health_score ASC
    """)
    road_health = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin_dashboard.html',
        total_complaints=total_complaints, pending=pending, in_progress=in_progress,
        completed=completed, total_roads=total_roads, total_length=total_length,
        road_stats=road_stats, cross_stats=cross_stats, complaint_types=complaint_types,
        daily_trends=daily_trends, severity_stats=severity_stats,
        recent_complaints=recent_complaints, village=village, road_health=road_health)

@app.route('/admin/complaints')
def admin_complaints():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    status_filter = request.args.get('status', '')
    road_filter = request.args.get('road', '')
    severity_filter = request.args.get('severity', '')
    
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT c.*, r.health_score FROM complaints c LEFT JOIN roads r ON c.road_id = r.id WHERE 1=1"
    params = []
    
    if status_filter:
        query += " AND c.status = ?"
        params.append(status_filter)
    if road_filter:
        query += " AND c.road_code = ?"
        params.append(road_filter)
    if severity_filter:
        query += " AND c.severity = ?"
        params.append(severity_filter)
    
    query += " ORDER BY c.id DESC"
    cursor.execute(query, params)
    complaints = cursor.fetchall()

    cursor.execute("SELECT road_code, road_name FROM roads ORDER BY road_code")
    roads = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin_complaints.html', complaints=complaints, roads=roads,
        status_filter=status_filter, road_filter=road_filter, severity_filter=severity_filter)

@app.route('/admin/complaint/<complaint_id>')
def admin_complaint_detail(complaint_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, r.health_score, r.length_m, r.width_m, r.road_type
        FROM complaints c
        LEFT JOIN roads r ON c.road_id = r.id
        WHERE c.complaint_id = ?
    """, (complaint_id,))
    complaint = cursor.fetchone()
    if not complaint:
        flash('Complaint not found.', 'warning')
        return redirect(url_for('admin_complaints'))
    
    cursor.execute("SELECT * FROM complaint_images WHERE complaint_id = ?", (complaint['id'],))
    images = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_complaint_detail.html', complaint=complaint, images=images)

@app.route('/admin/complaint/<complaint_id>/update', methods=['POST'])
def update_complaint_status(complaint_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    new_status = request.form.get('status', '')
    admin_remark = request.form.get('admin_remark', '')
    
    conn = get_db()
    cursor = conn.cursor()
    if new_status == 'Completed':
        cursor.execute("UPDATE complaints SET status=?, admin_remark=?, resolved_date=? WHERE complaint_id=?",
                       (new_status, admin_remark, date.today().strftime('%Y-%m-%d'), complaint_id))
    else:
        cursor.execute("UPDATE complaints SET status=?, admin_remark=? WHERE complaint_id=?",
                       (new_status, admin_remark, complaint_id))
    conn.commit()
    cursor.close()
    conn.close()
    flash(f'Complaint {complaint_id} updated to {new_status}.', 'success')
    return redirect(url_for('admin_complaint_detail', complaint_id=complaint_id))

@app.route('/admin/roads')
def admin_roads():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*,
               COUNT(c.id) as complaint_count,
               SUM(CASE WHEN c.status='Pending' THEN 1 ELSE 0 END) as pending_count
        FROM roads r
        LEFT JOIN complaints c ON r.id = c.road_id
        GROUP BY r.id
        ORDER BY r.road_code
    """)
    roads = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_roads.html', roads=roads)

@app.route('/admin/road/<road_code>')
def admin_road_detail(road_code):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM roads WHERE road_code = ?", (road_code,))
    road = cursor.fetchone()
    if not road:
        flash('Road not found.', 'warning')
        return redirect(url_for('admin_roads'))
    
    stats = get_road_stats(cursor, road['id'])

    cursor.execute("SELECT * FROM complaints WHERE road_id = ? ORDER BY id DESC", (road['id'],))
    complaints = cursor.fetchall()

    cursor.execute("""
        SELECT cr.cross_name, cr.cross_number, COUNT(c.id) as complaint_count
        FROM crosses cr
        LEFT JOIN complaints c ON cr.id = c.cross_id
        WHERE cr.road_id = ?
        GROUP BY cr.id
        ORDER BY cr.cross_number
    """, (road['id'],))
    cross_complaints = cursor.fetchall()

    cursor.execute("SELECT * FROM crosses WHERE road_id = ? ORDER BY cross_number", (road['id'],))
    crosses = cursor.fetchall()

    cursor.execute("""
        SELECT ri.*, r2.road_code as int_road_code, r2.road_name as int_road_name
        FROM road_intersections ri
        JOIN roads r2 ON ri.intersects_with_road_id = r2.id
        WHERE ri.road_id = ?
    """, (road['id'],))
    intersections = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('admin_road_detail.html', road=road, stats=stats, complaints=complaints,
        cross_complaints=cross_complaints, crosses=crosses, intersections=intersections)

@app.route('/admin/road/<road_code>/update-health', methods=['POST'])
def update_road_health(road_code):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    health_score = request.form.get('health_score', 100)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE roads SET health_score = ? WHERE road_code = ?", (int(health_score), road_code))
    conn.commit()
    cursor.close()
    conn.close()
    flash(f'Health score updated for {road_code}.', 'success')
    return redirect(url_for('admin_road_detail', road_code=road_code))

@app.route('/admin/analytics')
def admin_analytics():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.road_code, r.road_name, r.health_score,
               COUNT(c.id) as total,
               SUM(CASE WHEN c.status='Pending' THEN 1 ELSE 0 END) as pending,
               SUM(CASE WHEN c.status='Completed' THEN 1 ELSE 0 END) as completed
        FROM roads r
        LEFT JOIN complaints c ON r.id = c.road_id
        GROUP BY r.id
        ORDER BY r.health_score ASC
    """)
    road_health = cursor.fetchall()

    cursor.execute("""
        SELECT strftime('%Y-%m', date) as month, COUNT(*) as count
        FROM complaints
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month DESC
        LIMIT 6
    """)
    monthly_trends = cursor.fetchall()

    cursor.execute("""
        SELECT complaint_type, COUNT(*) as count
        FROM complaints
        GROUP BY complaint_type
        ORDER BY count DESC
    """)
    type_distribution = cursor.fetchall()

    cursor.execute("""
        SELECT r.road_name, cr.cross_name, COUNT(c.id) as count
        FROM complaints c
        JOIN crosses cr ON c.cross_id = cr.id
        JOIN roads r ON c.road_id = r.id
        GROUP BY r.road_name, cr.cross_name
        HAVING count > 0
        ORDER BY count DESC
        LIMIT 10
    """)
    hotspots = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('admin_analytics.html', road_health=road_health,
        monthly_trends=monthly_trends, type_distribution=type_distribution, hotspots=hotspots)

@app.route('/admin/generate-qr')
def generate_qr_codes():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM roads ORDER BY road_code")
    roads = cursor.fetchall()
    
    qr_folder = app.config['QR_FOLDER']
    os.makedirs(qr_folder, exist_ok=True)
    
    generated = []
    for road in roads:
        url = f"{Config.BASE_URL}/report?road={road['road_code']}"
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        filename = f"qr_{road['road_code']}.png"
        filepath = os.path.join(qr_folder, filename)
        img.save(filepath)
        cursor.execute("UPDATE roads SET qr_code_url = ?, qr_image_path = ? WHERE id = ?", (url, filename, road['id']))
        generated.append({'road': road['road_name'], 'code': road['road_code'], 'file': filename, 'url': url})
    
    conn.commit()
    cursor.close()
    conn.close()
    flash(f'Generated {len(generated)} QR codes successfully!', 'success')
    return render_template('admin_qr_generated.html', generated=generated)

@app.route('/qr/<filename>')
def serve_qr(filename):
    return send_from_directory(app.config['QR_FOLDER'], filename)

@app.route('/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/road-complaint-count')
def api_road_complaint_count():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.road_code, r.road_name, COUNT(c.id) as count
        FROM roads r
        LEFT JOIN complaints c ON r.id = c.road_id
        GROUP BY r.id
    """)
    data = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
