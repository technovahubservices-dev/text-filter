from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import json
import csv
import io
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

# Database configuration
DB_NAME = 'extractions.db'
SCHEMA_FILE = 'database_schema.sql'

def init_database():
    """Initialize the database with schema"""
    if not os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        with open(SCHEMA_FILE, 'r') as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()
        print("Database initialized successfully")

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/extractions', methods=['GET'])
def get_extractions():
    """Get all extractions with optional filtering"""
    search = request.args.get('search', '')
    date_filter = request.args.get('date_filter', '')
    
    conn = get_db_connection()
    query = "SELECT * FROM extractions WHERE 1=1"
    params = []
    
    if search:
        query += " AND filename LIKE ?"
        params.append(f'%{search}%')
    
    if date_filter:
        now = datetime.now()
        if date_filter == 'today':
            query += " AND DATE(extraction_date) = DATE(?)"
            params.append(now.strftime('%Y-%m-%d'))
        elif date_filter == 'week':
            week_ago = now - timedelta(days=7)
            query += " AND extraction_date >= ?"
            params.append(week_ago.strftime('%Y-%m-%d %H:%M:%S'))
        elif date_filter == 'month':
            month_ago = now - timedelta(days=30)
            query += " AND extraction_date >= ?"
            params.append(month_ago.strftime('%Y-%m-%d %H:%M:%S'))
    
    query += " ORDER BY extraction_date DESC"
    
    extractions = conn.execute(query, params).fetchall()
    conn.close()
    
    return jsonify({
        'extractions': [dict(extraction) for extraction in extractions]
    })

@app.route('/api/extractions', methods=['POST'])
def create_extraction():
    """Create a new extraction record"""
    data = request.get_json()
    
    if not data or not data.get('filename'):
        return jsonify({'error': 'Filename is required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO extractions (filename, file_size, mime_type, status, data_json)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        data['filename'],
        data.get('file_size'),
        data.get('mime_type', 'application/pdf'),
        data.get('status', 'success'),
        data.get('data_json')
    ))
    
    extraction_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Update metrics
    update_metrics()
    
    return jsonify({'id': extraction_id, 'message': 'Extraction created successfully'}), 201

@app.route('/api/extractions/<int:extraction_id>', methods=['GET'])
def get_extraction(extraction_id):
    """Get a specific extraction by ID"""
    conn = get_db_connection()
    extraction = conn.execute('SELECT * FROM extractions WHERE id = ?', (extraction_id,)).fetchone()
    conn.close()
    
    if extraction is None:
        return jsonify({'error': 'Extraction not found'}), 404
    
    return jsonify(dict(extraction))

@app.route('/api/extractions/<int:extraction_id>', methods=['DELETE'])
def delete_extraction(extraction_id):
    """Delete a specific extraction"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM extractions WHERE id = ?', (extraction_id,))
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': 'Extraction not found'}), 404
    
    conn.commit()
    conn.close()
    
    # Update metrics
    update_metrics()
    
    return jsonify({'message': 'Extraction deleted successfully'})

@app.route('/api/extractions/clear', methods=['DELETE'])
def clear_all_extractions():
    """Clear all extraction records"""
    conn = get_db_connection()
    conn.execute('DELETE FROM extractions')
    conn.commit()
    conn.close()
    
    # Update metrics
    update_metrics()
    
    return jsonify({'message': 'All extractions cleared successfully'})

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    """Get dashboard metrics"""
    conn = get_db_connection()
    
    # Total extractions
    total_result = conn.execute('SELECT COUNT(*) as count FROM extractions').fetchone()
    total_extractions = total_result['count']
    
    # This week's extractions
    week_ago = datetime.now() - timedelta(days=7)
    week_result = conn.execute(
        'SELECT COUNT(*) as count FROM extractions WHERE extraction_date >= ?',
        (week_ago.strftime('%Y-%m-%d %H:%M:%S'),)
    ).fetchone()
    this_week = week_result['count']
    
    # Average file size
    size_result = conn.execute(
        'SELECT AVG(file_size) as avg_size FROM extractions WHERE file_size IS NOT NULL'
    ).fetchone()
    avg_size = size_result['avg_size']
    avg_size_mb = f"{(avg_size / 1024 / 1024):.1f} MB" if avg_size else "—"
    
    # Success rate
    success_result = conn.execute(
        'SELECT COUNT(*) as count FROM extractions WHERE status = "success"'
    ).fetchone()
    success_count = success_result['count']
    success_rate = f"{(success_count / total_extractions * 100):.1f}%" if total_extractions > 0 else "100%"
    
    conn.close()
    
    return jsonify({
        'total_extractions': total_extractions,
        'this_week': this_week,
        'avg_size': avg_size_mb,
        'success_rate': success_rate
    })

@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    """Export extractions to CSV"""
    search = request.args.get('search', '')
    date_filter = request.args.get('date_filter', '')
    
    conn = get_db_connection()
    query = "SELECT id, filename, extraction_date, file_size, status FROM extractions WHERE 1=1"
    params = []
    
    if search:
        query += " AND filename LIKE ?"
        params.append(f'%{search}%')
    
    if date_filter:
        now = datetime.now()
        if date_filter == 'today':
            query += " AND DATE(extraction_date) = DATE(?)"
            params.append(now.strftime('%Y-%m-%d'))
        elif date_filter == 'week':
            week_ago = now - timedelta(days=7)
            query += " AND extraction_date >= ?"
            params.append(week_ago.strftime('%Y-%m-%d %H:%M:%S'))
        elif date_filter == 'month':
            month_ago = now - timedelta(days=30)
            query += " AND extraction_date >= ?"
            params.append(month_ago.strftime('%Y-%m-%d %H:%M:%S'))
    
    query += " ORDER BY extraction_date DESC"
    
    extractions = conn.execute(query, params).fetchall()
    conn.close()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['ID', 'Filename', 'Date', 'Size (MB)', 'Status'])
    
    # Data
    for extraction in extractions:
        size_mb = f"{(extraction['file_size'] / 1024 / 1024):.1f}" if extraction['file_size'] else "—"
        writer.writerow([
            extraction['id'],
            extraction['filename'],
            extraction['extraction_date'],
            size_mb,
            extraction['status']
        ])
    
    output.seek(0)
    
    # Create response
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    
    return send_file(
        mem,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'extractions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

def update_metrics():
    """Update system metrics"""
    conn = get_db_connection()
    
    # Update total extractions
    total_result = conn.execute('SELECT COUNT(*) as count FROM extractions').fetchone()
    conn.execute('''
        INSERT OR REPLACE INTO metrics (metric_name, metric_value, recorded_at)
        VALUES ('total_extractions', ?, CURRENT_TIMESTAMP)
    ''', (str(total_result['count']),))
    
    # Update last updated timestamp
    conn.execute('''
        INSERT OR REPLACE INTO metrics (metric_name, metric_value, recorded_at)
        VALUES ('last_updated', datetime('now'), CURRENT_TIMESTAMP)
    ''')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    # Initialize database on startup
    init_database()
    print("Starting Flask server on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
