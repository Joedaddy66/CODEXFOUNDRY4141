# RA Longevity MLOps Microservice

A FastAPI-based microservice for serving RA Longevity analysis artifacts, providing endpoints for data analysis, report retrieval, and model deployment.

## Features

- **POST /api/longevity/analyze**: Analyze CSV or JSON data with RA feature encoding
- **GET /api/longevity/report/{run_id}**: Retrieve analysis reports (JSON or HTML)
- **POST /api/longevity/deploy**: Deploy models with DKIL validation
- **Bearer Token Authentication**: Secure all endpoints
- **Automatic Artifact Management**: Generate and serve reports, JSON, and bundles
- **DKIL (Data Knowledge Integrity Lock)**: Validate data integrity before serving/deploying

## Installation

### Prerequisites

- Python 3.9+
- pip

### Setup

1. Clone the repository:
```bash
git clone https://github.com/Joedaddy66/CODEXFOUNDRY4141.git
cd CODEXFOUNDRY4141
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables (optional):
```bash
export API_BEARER_TOKEN="your-secure-token-here"
```

## Running the Server

### Development Mode

```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

The server will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- **Interactive API docs**: http://localhost:8000/docs
- **Alternative docs**: http://localhost:8000/redoc

## Endpoints

### 1. POST /api/longevity/analyze

Accepts CSV upload or JSON tabular data, applies RA feature encoding, and returns predictions.

**Headers:**
```
Authorization: Bearer <your-token>
```

**Request (CSV Upload):**
```bash
curl -X POST "http://localhost:8000/api/longevity/analyze" \
  -H "Authorization: Bearer demo-token-replace-in-production" \
  -F "file=@data.csv"
```

**Request (JSON Data):**
```bash
curl -X POST "http://localhost:8000/api/longevity/analyze" \
  -H "Authorization: Bearer demo-token-replace-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {"value": 10, "metric": 20},
      {"value": 15, "metric": 25},
      {"value": 20, "metric": 30}
    ],
    "mode": "tabular"
  }'
```

**Response:**
```json
{
  "run_id": "123e4567-e89b-12d3-a456-426614174000",
  "predictions": [0.82, 0.85, 0.88],
  "ldrop_metrics": {
    "mean_prediction": 0.85,
    "std_prediction": 0.025,
    "ldrop_threshold": 0.5,
    "samples_below_threshold": 0
  },
  "ra_score_deltas": {
    "ra_mean": 0.67,
    "ra_std": 0.15,
    "ra_delta_mean": 0.02
  },
  "timestamp": "2025-10-29T07:19:02.933Z"
}
```

**RA Features Encoded:**
- **RA** (Relative Activity): Normalized activity metric
- **D** (Delta): Change between consecutive values
- **M** (Momentum): Rolling mean of deltas
- **S** (Stability): Rolling standard deviation
- **LR** (Learning Rate): Exponential moving average

### 2. GET /api/longevity/report/{run_id}

Retrieves the analysis report for a specific run.

**Headers:**
```
Authorization: Bearer <your-token>
```

**Request (JSON format):**
```bash
curl -X GET "http://localhost:8000/api/longevity/report/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer demo-token-replace-in-production"
```

**Request (HTML format):**
```bash
curl -X GET "http://localhost:8000/api/longevity/report/123e4567-e89b-12d3-a456-426614174000?format=html" \
  -H "Authorization: Bearer demo-token-replace-in-production"
```

**Features:**
- Returns JSON report by default
- Add `?format=html` for HTML report
- Validates DKIL lock if present
- Returns 403 if DKIL validation fails

### 3. POST /api/longevity/deploy

Deploys a model to the model registry with DKIL validation.

**Headers:**
```
Authorization: Bearer <your-token>
```

**Request:**
```bash
curl -X POST "http://localhost:8000/api/longevity/deploy" \
  -H "Authorization: Bearer demo-token-replace-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "123e4567-e89b-12d3-a456-426614174000",
    "human_key": "human-approval-key-12345678",
    "logic_key": "logic-validation-key-87654321",
    "model_name": "ra_longevity_v1"
  }'
```

**Response:**
```json
{
  "status": "success",
  "message": "Model ra_longevity_v1 deployed successfully",
  "run_id": "123e4567-e89b-12d3-a456-426614174000",
  "model_name": "ra_longevity_v1",
  "deployed_at": "2025-10-29T07:19:02.933Z",
  "bundle_path": "/artifacts/123e4567-e89b-12d3-a456-426614174000/bundle.zip"
}
```

**Requirements:**
- Valid run_id with existing artifacts
- DKIL lock file must exist and pass validation
- Both human_key and logic_key must be at least 8 characters
- Dual-key approval ensures human oversight and automated validation

### 4. GET /artifacts/{run_id}/{filename}

Static file serving for artifacts.

**Example:**
```bash
# Download bundle
curl -O "http://localhost:8000/artifacts/123e4567-e89b-12d3-a456-426614174000/bundle.zip"

# View HTML report
curl "http://localhost:8000/artifacts/123e4567-e89b-12d3-a456-426614174000/report.html"
```

## Authentication

All endpoints require Bearer token authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-token>
```

Default token (development only): `demo-token-replace-in-production`

**Production Setup:**
Set a secure token via environment variable:
```bash
export API_BEARER_TOKEN="your-secure-random-token"
```

## Artifacts Structure

After analysis, artifacts are stored in `/artifacts/{run_id}/`:

```
artifacts/
└── {run_id}/
    ├── results.json       # Analysis results
    ├── report.html        # HTML report
    ├── dkil_lock.json    # DKIL integrity lock (if threshold met)
    ├── deployment.json    # Deployment record (after deploy)
    └── bundle.zip         # Complete bundle of all artifacts
```

## DKIL (Data Knowledge Integrity Lock)

DKIL ensures data quality and integrity before deployment:

1. **Creation**: Generated during analysis if quality thresholds are met
2. **Validation**: Checked before serving reports or deploying models
3. **Criteria**: 
   - Integrity check passed
   - Less than 30% of samples below L-drop threshold

**DKIL Lock File Example:**
```json
{
  "run_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-10-29T07:19:02.933Z",
  "integrity_check": true,
  "threshold_met": true,
  "ldrop_threshold": 0.5,
  "samples_below_threshold": 5
}
```

## Error Handling

The API uses standard HTTP status codes:

- **200**: Success
- **400**: Bad request (missing required fields, invalid data)
- **401**: Unauthorized (missing or invalid token)
- **403**: Forbidden (DKIL validation failed)
- **404**: Not found (run_id doesn't exist)
- **500**: Internal server error

## Deployment

### Docker (Coming Soon)

```bash
docker build -t ra-longevity-api .
docker run -p 8000:8000 -e API_BEARER_TOKEN="your-token" ra-longevity-api
```

### Cloud Run (Google Cloud)

```bash
gcloud run deploy ra-longevity-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars API_BEARER_TOKEN="your-token"
```

### Firebase Functions

```bash
firebase deploy --only functions
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
# Format code
black main.py

# Lint
pylint main.py
```

## License

See LICENSE file for details.

## Support

For issues and questions, please open an issue on GitHub.
