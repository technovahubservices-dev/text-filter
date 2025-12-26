#!/usr/bin/env python3
"""
Database Initialization Script
This script initializes the SQLite database for the PDF extraction dashboard.
"""

import sqlite3
import os
import sys

def init_database():
    """Initialize the database with schema"""
    db_name = 'extractions.db'
    schema_file = 'database_schema.sql'
    
    # Check if schema file exists
    if not os.path.exists(schema_file):
        print(f"Error: Schema file '{schema_file}' not found!")
        sys.exit(1)
    
    # Remove existing database if it exists
    if os.path.exists(db_name):
        print(f"Removing existing database '{db_name}'...")
        os.remove(db_name)
    
    # Create new database
    print(f"Initializing database '{db_name}'...")
    conn = sqlite3.connect(db_name)
    
    try:
        # Read and execute schema
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        conn.executescript(schema_sql)
        conn.commit()
        
        # Verify tables were created
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"Database initialized successfully!")
        print(f"Created tables: {[table[0] for table in tables]}")
        
        # Insert sample data for testing
        print("Adding sample data...")
        sample_data = [
            ('sample_report_1.pdf', 1024000, 'application/pdf', 'success', '{"title": "Sample Report 1", "pages": 10}'),
            ('sample_report_2.pdf', 2048000, 'application/pdf', 'success', '{"title": "Sample Report 2", "pages": 20}'),
            ('sample_report_3.pdf', 512000, 'application/pdf', 'failed', '{"error": "Corrupted file"}'),
        ]
        
        cursor.executemany('''
            INSERT INTO extractions (filename, file_size, mime_type, status, data_json)
            VALUES (?, ?, ?, ?, ?)
        ''', sample_data)
        
        conn.commit()
        print(f"Added {len(sample_data)} sample records")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        conn.rollback()
        sys.exit(1)
    
    finally:
        conn.close()

def verify_database():
    """Verify database structure and data"""
    db_name = 'extractions.db'
    
    if not os.path.exists(db_name):
        print(f"Database '{db_name}' does not exist!")
        return
    
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    try:
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\nDatabase structure:")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"  Table '{table_name}': {[col[1] for col in columns]}")
        
        # Check data
        cursor.execute("SELECT COUNT(*) FROM extractions")
        count = cursor.fetchone()[0]
        print(f"\nData summary:")
        print(f"  Total extractions: {count}")
        
        if count > 0:
            cursor.execute("SELECT filename, status, extraction_date FROM extractions ORDER BY extraction_date DESC LIMIT 5")
            recent = cursor.fetchall()
            print(f"  Recent extractions:")
            for row in recent:
                print(f"    - {row[0]} ({row[1]}) on {row[2]}")
        
    except Exception as e:
        print(f"Error verifying database: {e}")
    
    finally:
        conn.close()

if __name__ == '__main__':
    print("PDF Extraction Dashboard - Database Initialization")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--verify':
        verify_database()
    else:
        init_database()
        verify_database()
    
    print("\nDatabase setup complete!")
    print("You can now start the Flask server with: python app.py")
