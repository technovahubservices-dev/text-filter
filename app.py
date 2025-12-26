from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import csv
import io
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

# -------------------------------
# Basic Routes
# -------------------------------

@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "message": "Text Filter API is running"
    })

# @app.route("/favicon.ico")
# def favicon():
#     return "", 204

# -------------------------------
# Database configuration
# -------------------------------

DB_NAME = "/tmp/extractions.db"
SCHEMA_FILE = "database_schema.sql"

def init_database():
    if not os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        with open(SCHEMA_FILE, 'r') as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# -------------------------------
# API Routes
# -------------------------------

@app.route('/api/extractions', methods=['GET'])
def get_extractions():
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
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    return jsonify({"extractions": [dict(r) for r in rows]})

@app.route('/api/extractions', methods=['POST'])
def create_extraction():
    data = request.get_json()
    if not data or not data.get('filename'):
        return jsonify({"error": "Filename is required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO extractions (filename, file_size, mime_type, status, data_json)
        VALUES (?, ?, ?, ?, ?)
    """, (
        data['filename'],
        data.get('file_size'),
        data.get('mime_type', 'application/pdf'),
        data.get('status', 'success'),
        data.get('data_json')
    ))
    
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    update_metrics()
    
    return jsonify({"id": new_id, "message": "Extraction created"}), 201

@app.route('/api/extractions/<int:extraction_id>', methods=['GET'])
def get_extraction(extraction_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM extractions WHERE id = ?", (extraction_id,)).fetchone()
    conn.close()
    
    if not row:
        return jsonify({"error": "Not found"}), 404
    
    return jsonify(dict(row))

@app.route('/api/extractions/<int:extraction_id>', methods=['DELETE'])
def delete_extraction(extraction_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM extractions WHERE id = ?", (extraction_id,))
    
    if cur.rowcount == 0:
        conn.close()
        return jsonify({"error": "Not found"}), 404
    
    conn.commit()
    conn.close()
    update_metrics()
    
    return jsonify({"message": "Deleted"})

@app.route('/api/extractions/clear', methods=['DELETE'])
def clear_all_extractions():
    conn = get_db_connection()
    conn.execute("DELETE FROM extractions")
    conn.commit()
    conn.close()
    
    update_metrics()
    return jsonify({"message": "All cleared"})

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    conn = get_db_connection()
    
    total = conn.execute("SELECT COUNT(*) AS c FROM extractions").fetchone()["c"]
    week_ago = datetime.now() - timedelta(days=7)
    week = conn.execute(
        "SELECT COUNT(*) AS c FROM extractions WHERE extraction_date >= ?",
        (week_ago.strftime('%Y-%m-%d %H:%M:%S'),)
    ).fetchone()["c"]
    
    avg = conn.execute(
        "SELECT AVG(file_size) AS a FROM extractions WHERE file_size IS NOT NULL"
    ).fetchone()["a"]
    
    success = conn.execute(
        "SELECT COUNT(*) AS c FROM extractions WHERE status='success'"
    ).fetchone()["c"]
    
    conn.close()
    
    return jsonify({
        "total_extractions": total,
        "this_week": week,
        "avg_size": f"{(avg/1024/1024):.1f} MB" if avg else "—",
        "success_rate": f"{(success/total*100):.1f}%" if total else "100%"
    })

@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT id, filename, extraction_date, file_size, status
        FROM extractions ORDER BY extraction_date DESC
    """).fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Filename", "Date", "Size (MB)", "Status"])
    
    for r in rows:
        size = f"{(r['file_size']/1024/1024):.1f}" if r['file_size'] else "—"
        writer.writerow([r["id"], r["filename"], r["extraction_date"], size, r["status"]])
    
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    mem.seek(0)
    
    return send_file(mem, mimetype="text/csv", as_attachment=True,
                     download_name=f"extractions_{datetime.now():%Y%m%d_%H%M%S}.csv")

# -------------------------------
# Metrics
# -------------------------------

def update_metrics():
    conn = get_db_connection()
    total = conn.execute("SELECT COUNT(*) AS c FROM extractions").fetchone()["c"]
    
    conn.execute("""
        INSERT OR REPLACE INTO metrics (metric_name, metric_value, recorded_at)
        VALUES ('total_extractions', ?, CURRENT_TIMESTAMP)
    """, (str(total),))
    
    conn.execute("""
        INSERT OR REPLACE INTO metrics (metric_name, metric_value, recorded_at)
        VALUES ('last_updated', datetime('now'), CURRENT_TIMESTAMP)
    """)
    
    conn.commit()
    conn.close()

# Initialize DB at import time (Vercel safe)
init_database()
