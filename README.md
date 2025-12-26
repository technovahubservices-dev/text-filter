# PDF Extraction Dashboard Database

This project provides a complete database solution for storing and managing PDF extraction data for the Technova Hub dashboard.

## Files Created

- **`database_schema.sql`** - SQLite database schema with tables for extractions, metrics, and error logs
- **`app.py`** - Flask REST API server with endpoints for dashboard operations
- **`init_db.py`** - Database initialization script with sample data
- **`requirements.txt`** - Python dependencies

## Database Schema

### Tables

1. **`extractions`** - Stores PDF extraction records
   - `id` - Primary key
   - `filename` - Original filename
   - `extraction_date` - When extraction was performed
   - `file_size` - File size in bytes
   - `mime_type` - File MIME type
   - `status` - success/failed/processing
   - `data_json` - Extracted data in JSON format

2. **`metrics`** - Dashboard metrics cache
   - `metric_name` - Name of metric
   - `metric_value` - Metric value
   - `recorded_at` - Timestamp

3. **`error_logs`** - Error tracking (optional)
   - Links to extractions for debugging

## API Endpoints

### Extractions
- `GET /api/extractions` - Get all extractions (supports search and date filtering)
- `POST /api/extractions` - Create new extraction record
- `GET /api/extractions/{id}` - Get specific extraction
- `DELETE /api/extractions/{id}` - Delete extraction
- `DELETE /api/extractions/clear` - Clear all extractions

### Metrics
- `GET /api/metrics` - Get dashboard metrics (total, weekly, avg size, success rate)

### Export
- `GET /api/export/csv` - Export extractions to CSV

## Setup Instructions

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize database:**
   ```bash
   python init_db.py
   ```

3. **Start the API server:**
   ```bash
   python app.py
   ```

4. **Access the dashboard:**
   - Open `dashboard.html` in your browser
   - The API will be available at `http://localhost:5000`

## Features

- **SQLite database** - No external database required
- **RESTful API** - Complete CRUD operations
- **Real-time metrics** - Dashboard statistics
- **Search & filtering** - By filename and date ranges
- **CSV export** - Data export functionality
- **Error tracking** - Optional error logging
- **Sample data** - Pre-populated for testing

## Integration

The dashboard HTML files (`dashboard.html` and `report_interface.html`) are already configured to communicate with this API at `http://localhost:5000`. The database will automatically store extraction data when users upload PDFs through the interface.
