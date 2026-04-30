from flask import Flask, request, jsonify
import mysql.connector
from datetime import datetime

app = Flask(__name__)

DB_CONFIG = {
    'host': 'YOUR_DB_HOST',
    'user': 'YOUR_DB_USER',
    'password': 'YOUR_DB_PASSWORD',
    'database': 'attendance_db'
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def format_time_arabic(dt):
    hour = dt.hour
    minute = dt.strftime('%M')
    if hour == 0: return f"12:{minute} ص"
    elif hour < 12: return f"{hour}:{minute} ص"
    elif hour == 12: return f"12:{minute} م"
    else: return f"{hour - 12}:{minute} م"

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT e.*, c.name as company_name, c.latitude, c.longitude, 
                   c.geofence_radius, c.logo_url, c.primary_color
            FROM employees e
            JOIN companies c ON e.company_id = c.id
            WHERE e.code = %s AND c.code = %s AND c.is_active = 1
        """, (data['employee_id'], data['company_code']))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return jsonify({'status': 'error', 'message': 'كود خاطئ'})
        return jsonify({
            'status': 'success',
            'employee': {
                'id': str(row['id']),
                'name': row['name'],
                'code': row['code'],
                'role': row['role'],
                'type': row['type'],
                'shift': row['shift'],
                'home_lat': float(row['home_lat'] or 0),
                'home_lng': float(row['home_lng'] or 0),
                'home_wifi': row['home_wifi'] or '',
                'device_id': row['device_id'] or '',
                'token': 'token_' + str(row['id'])
            },
            'company': {
                'id': str(row['company_id']),
                'name': row['company_name'],
                'code': data['company_code'],
                'logo_url': row['logo_url'] or '',
                'primary_color': row['primary_color'] or '#1A237E',
                'latitude': float(row['latitude']),
                'longitude': float(row['longitude']),
                'geofence_radius': float(row['geofence_radius'])
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/attendance', methods=['POST'])
def attendance():
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()
        timestamp = datetime.fromisoformat(data['timestamp'])
        work_date = timestamp.date()
        arabic_time = format_time_arabic(timestamp)
        if data['type'] == 'CHECK_IN':
            cursor.execute("""
                INSERT INTO attendance (employee_id, check_in, work_date, latitude, longitude, wifi_ssid)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (data['employee_id'], arabic_time, work_date,
                  data.get('latitude'), data.get('longitude'), data.get('wifi_ssid')))
        else:
            cursor.execute("""
                UPDATE attendance SET check_out = %s
                WHERE employee_id = %s AND work_date = %s
                ORDER BY id DESC LIMIT 1
            """, (arabic_time, data['employee_id'], work_date))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/employee/stats', methods=['GET'])
def stats():
    try:
        employee_id = request.args.get('employee_id')
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN check_in IS NOT NULL THEN 1 END) as attendance_days,
                COUNT(CASE WHEN check_in IS NULL THEN 1 END) as absence_days
            FROM attendance
            WHERE employee_id = %s
        """, (employee_id,))
        row = cursor.fetchone()
        conn.close()
        return jsonify({
            'status': 'success',
            'attendance_days': row['attendance_days'],
            'absence_days': row['absence_days'],
            'vacation_balance': 14,
            'late_hours': '0:00'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
