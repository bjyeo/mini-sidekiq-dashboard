# Mini Sidekiq Dashboard

A lightweight job queue system built with FastAPI and Supabase, inspired by Sidekiq. Submit jobs via REST API, process them with Python workers, and monitor job status in real-time.

## Features

- **REST API** for job management
- **Job Queue** with priority handling
- **Status Tracking** (pending, running, completed, failed, cancelled)
- **Retry Logic** with exponential backoff
- **Dead Letter Queue** for failed jobs
- **Real-time Dashboard** capabilities
- **Python Workers** for job processing
- **PostgreSQL Storage** via Supabase

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP/REST
       ▼
┌─────────────────┐      ┌──────────────┐
│   API Service   │◄────►│   Supabase   │
│   (FastAPI)     │      │ (PostgreSQL) │
└─────────────────┘      └──────┬───────┘
                                │
                                ▼
                      ┌──────────────────┐
                      │  Worker Service  │
                      │    (Python)      │
                      └──────────────────┘
```

## API Endpoints

### Jobs
- `POST /jobs` - Create a new job
- `GET /jobs` - List all jobs (with pagination)
- `GET /jobs/pending` - Get pending jobs for workers
- `GET /jobs/{job_id}` - Get job by ID
- `PATCH /jobs/{job_id}/status` - Update job status
- `DELETE /jobs/{job_id}` - Delete a job

### Health
- `GET /health` - Health check

## Setup

### Prerequisites

- Python 3.13
- Supabase

### Installation

1. Clone the repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file with:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_DB_PASSWORD=your_database_password
```

4. Initialize the database:
Run the SQL scripts in order:
```bash
# Connect to Supabase and run:
# 1. database/schema.sql
# 2. database/database_functions.sql
```

## Usage

### Running the API Server

```bash
uvicorn src.api.main:app --reload
```

The API server will start at `http://localhost:8000`

- **API Documentation (Swagger)**: `http://localhost:8000/docs`

### Creating a Job

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "send_email",
    "payload": {
      "to": "user@example.com",
      "subject": "Hello"
    },
    "priority": 1
  }'
```

### Getting Job Status

```bash
curl http://localhost:8000/jobs/{job_id}
```

### Updating Job Status

```bash
curl -X PATCH http://localhost:8000/jobs/{job_id}/status \
  -H "Content-Type: application/json" \
  -d '{"status": "running"}'
```

## Testing

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
coverage run -m pytest
coverage report
```

## Project Structure

```
sidekiq-dashboard/
├── src/
│   ├── api/              # FastAPI application and endpoints
│   ├── config/           # Configuration management
│   ├── database/         # Database connection
│   ├── models/           # Data models and enums
│   ├── processors/       # Job processors (to be implemented)
│   ├── repositories/     # Data access layer
│   ├── services/         # Business logic (to be implemented)
│   └── tests/
│       └── integration/  # Integration tests
├── database/             # SQL schema and functions
├── worker/              # Worker service (to be implemented)
├── requirements.txt     # Python dependencies
└── pytest.ini          # Test configuration
```

## Database Schema

### Jobs Table
- `id` - UUID (PK)
- `type` - Job type identifier
- `payload` - JSONB job data
- `status` - Job status (pending/running/completed/failed/cancelled)
- `priority` - Job priority (higher = more important)
- `retry_count` - Current retry attempt
- `max_retries` - Maximum retry attempts
- `error_message` - Error details if failed
- Timestamps: `created_at`, `updated_at`, `scheduled_at`, `started_at`, `completed_at`

### Job Logs Table
- `id` - UUID (PK)
- `job_id` - UUID (FK to jobs)
- `message` - Log message
- `level` - Log level (info/warning/error/debug)
- `created_at` - Timestamp

## Configuration

Environment variables:

- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase anon key
- `SUPABASE_DB_PASSWORD` - Database password
- `WORKER_POLL_INTERVAL` - Worker polling interval (default: 5s)
- `WORKER_BATCH_SIZE` - Jobs per batch (default: 10)
- `WORKER_CONCURRENCY` - Concurrent workers (default: 4)
- `DEFAULT_MAX_RETRIES` - Default retry limit (default: 3)
- `JOB_TIMEOUT` - Job timeout in seconds (default: 300)