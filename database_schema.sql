-- SQLite Database Schema for PDF Extraction Dashboard
-- Created for Technova Hub Text Extraction System

-- Table to store PDF extraction records
CREATE TABLE IF NOT EXISTS extractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename VARCHAR(255) NOT NULL,
    extraction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    file_size INTEGER, -- in bytes
    mime_type VARCHAR(100) DEFAULT 'application/pdf',
    status VARCHAR(50) DEFAULT 'success', -- success, failed, processing
    data_json TEXT, -- extracted data in JSON format
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Table to store system metrics for dashboard
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name VARCHAR(100) NOT NULL,
    metric_value TEXT NOT NULL,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Table to store error logs (optional for debugging)
CREATE TABLE IF NOT EXISTS error_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    extraction_id INTEGER,
    error_message TEXT,
    error_details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (extraction_id) REFERENCES extractions(id) ON DELETE SET NULL
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_extractions_date ON extractions(extraction_date);
CREATE INDEX IF NOT EXISTS idx_extractions_filename ON extractions(filename);
CREATE INDEX IF NOT EXISTS idx_extractions_status ON extractions(status);
CREATE INDEX IF NOT EXISTS idx_metrics_name_date ON metrics(metric_name, recorded_at);

-- Trigger to update the updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_extractions_timestamp 
    AFTER UPDATE ON extractions
    FOR EACH ROW
BEGIN
    UPDATE extractions SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Insert initial metrics record
INSERT OR IGNORE INTO metrics (metric_name, metric_value) VALUES ('total_extractions', '0');
INSERT OR IGNORE INTO metrics (metric_name, metric_value) VALUES ('last_updated', datetime('now'));
