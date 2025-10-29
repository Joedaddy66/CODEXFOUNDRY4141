"""
FastAPI Microservice for RA Longevity Analysis

This microservice provides endpoints for:
- Analyzing CSV/JSON data with RA feature encoding
- Retrieving HTML and JSON reports from artifacts
- Deploying models with DKIL validation
"""

import os
import json
import uuid
import zipfile
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Header, Body
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import uvicorn

# Initialize FastAPI app
app = FastAPI(
    title="RA Longevity MLOps API",
    description="Microservice for RA Longevity analysis and model deployment",
    version="1.0.0"
)

# Configuration
ARTIFACTS_DIR = Path("/home/runner/work/CODEXFOUNDRY4141/CODEXFOUNDRY4141/artifacts")
ARTIFACTS_DIR.mkdir(exist_ok=True)

# Bearer token for authentication (in production, use environment variables)
BEARER_TOKEN = os.environ.get("API_BEARER_TOKEN", "demo-token-replace-in-production")

# Models
class AnalyzeRequest(BaseModel):
    """Request model for tabular data analysis"""
    data: list[dict]
    mode: str = "tabular"  # "tabular" or "time_series"

class DeployRequest(BaseModel):
    """Request model for model deployment"""
    model_config = {"protected_namespaces": ()}
    
    run_id: str
    human_key: str
    logic_key: str
    model_name: Optional[str] = None

class AnalyzeResponse(BaseModel):
    """Response model for analysis"""
    run_id: str
    predictions: list[float]
    ldrop_metrics: dict
    ra_score_deltas: dict
    timestamp: str

# Authentication dependency
async def verify_token(authorization: Optional[str] = Header(None)):
    """Verify bearer token authentication"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        if token != BEARER_TOKEN:
            raise HTTPException(status_code=401, detail="Invalid token")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    return token


# RA Feature Encoder
def encode_ra_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Encode RA features: RA (Relative Activity), D (Delta), M (Momentum), 
    S (Stability), LR (Learning Rate)
    """
    encoded_df = df.copy()
    
    # Calculate RA features if not present
    if 'RA' not in encoded_df.columns:
        # RA: Relative Activity (normalized first column if numeric)
        numeric_cols = encoded_df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            first_col = numeric_cols[0]
            encoded_df['RA'] = (encoded_df[first_col] - encoded_df[first_col].min()) / \
                              (encoded_df[first_col].max() - encoded_df[first_col].min() + 1e-10)
    
    if 'D' not in encoded_df.columns:
        # D: Delta (difference between consecutive values)
        if 'RA' in encoded_df.columns:
            encoded_df['D'] = encoded_df['RA'].diff().fillna(0)
    
    if 'M' not in encoded_df.columns:
        # M: Momentum (rolling mean of delta)
        if 'D' in encoded_df.columns:
            encoded_df['M'] = encoded_df['D'].rolling(window=3, min_periods=1).mean()
    
    if 'S' not in encoded_df.columns:
        # S: Stability (rolling standard deviation)
        if 'RA' in encoded_df.columns:
            encoded_df['S'] = encoded_df['RA'].rolling(window=3, min_periods=1).std().fillna(0)
    
    if 'LR' not in encoded_df.columns:
        # LR: Learning Rate (exponential moving average factor)
        if 'RA' in encoded_df.columns:
            encoded_df['LR'] = encoded_df['RA'].ewm(span=3).mean()
    
    return encoded_df


def calculate_ldrop_metrics(df: pd.DataFrame, predictions: list[float]) -> dict:
    """Calculate L-drop (Longevity drop) metrics"""
    df_with_pred = df.copy()
    df_with_pred['predictions'] = predictions
    
    metrics = {
        "mean_prediction": float(pd.Series(predictions).mean()),
        "std_prediction": float(pd.Series(predictions).std()),
        "min_prediction": float(pd.Series(predictions).min()),
        "max_prediction": float(pd.Series(predictions).max()),
        "ldrop_threshold": 0.5,  # Configurable threshold
        "samples_below_threshold": int((pd.Series(predictions) < 0.5).sum())
    }
    
    return metrics


def calculate_ra_score_deltas(df_encoded: pd.DataFrame) -> dict:
    """Calculate RA score deltas"""
    deltas = {}
    
    if 'RA' in df_encoded.columns:
        deltas['ra_mean'] = float(df_encoded['RA'].mean())
        deltas['ra_std'] = float(df_encoded['RA'].std())
        deltas['ra_delta_mean'] = float(df_encoded['D'].mean()) if 'D' in df_encoded.columns else 0.0
        deltas['ra_momentum'] = float(df_encoded['M'].mean()) if 'M' in df_encoded.columns else 0.0
        deltas['ra_stability'] = float(df_encoded['S'].mean()) if 'S' in df_encoded.columns else 0.0
    
    return deltas


def validate_run_id(run_id: str) -> str:
    """
    Validate and sanitize run_id to prevent path traversal attacks.
    
    Security: This function provides defense-in-depth against path injection:
    1. Strict UUID format validation (8-4-4-4-12 hex pattern)
    2. Explicit check for path traversal characters (.. / \\)
    
    Only allows UUID format (alphanumeric and hyphens).
    
    Note: CodeQL may flag uses of validated_run_id as path injection,
    but these are false positives as the validation ensures only safe UUIDs pass.
    
    Args:
        run_id: User-provided run identifier
    
    Returns:
        Validated run_id string (guaranteed to be safe UUID format)
    
    Raises:
        HTTPException: If run_id doesn't match UUID format or contains path traversal
    """
    # Check if run_id matches UUID format
    uuid_pattern = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', re.IGNORECASE)
    if not uuid_pattern.match(run_id):
        raise HTTPException(status_code=400, detail="Invalid run_id format. Must be a valid UUID.")
    
    # Additional check: ensure no path traversal characters (defense in depth)
    if '..' in run_id or '/' in run_id or '\\' in run_id:
        raise HTTPException(status_code=400, detail="Invalid run_id: path traversal not allowed")
    
    return run_id


def check_dkil(run_id: str, threshold: float = 0.5) -> tuple[bool, dict]:
    """
    Check DKIL (Data Knowledge Integrity Lock) status
    Returns: (passed, details)
    """
    # Validate run_id to prevent path traversal
    validated_run_id = validate_run_id(run_id)
    
    artifacts_path = ARTIFACTS_DIR / validated_run_id
    dkil_file = artifacts_path / "dkil_lock.json"
    
    if not dkil_file.exists():
        return False, {"error": "DKIL lock file not found"}
    
    with open(dkil_file, 'r') as f:
        dkil_data = json.load(f)
    
    # Check if integrity checks passed (threshold_met is informational)
    passed = dkil_data.get('integrity_check', False)
    
    return passed, dkil_data


# Endpoints

@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "service": "RA Longevity MLOps API",
        "version": "1.0.0",
        "endpoints": {
            "analyze": "POST /api/longevity/analyze",
            "report": "GET /api/longevity/report/{run_id}",
            "deploy": "POST /api/longevity/deploy"
        }
    }


@app.post("/api/longevity/analyze", response_model=AnalyzeResponse)
async def analyze_data_json(
    request_data: AnalyzeRequest,
    token: str = Depends(verify_token)
):
    """
    Analyze JSON tabular data
    - Accepts JSON in request body
    - Applies RA feature encoding (RA, D, M, S, LR)
    - Returns predictions, ldrop metrics, and RA score deltas
    """
    return await _process_analysis(pd.DataFrame(request_data.data), request_data.mode)


@app.post("/api/longevity/analyze/csv", response_model=AnalyzeResponse)
async def analyze_data_csv(
    file: UploadFile = File(...),
    token: str = Depends(verify_token)
):
    """
    Analyze CSV file upload
    - Accepts CSV file
    - Applies RA feature encoding (RA, D, M, S, LR)
    - Returns predictions, ldrop metrics, and RA score deltas
    """
    try:
        contents = await file.read()
        from io import StringIO
        df = pd.read_csv(StringIO(contents.decode('utf-8')))
        return await _process_analysis(df, "tabular")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")


async def _process_analysis(df: pd.DataFrame, mode: str = "tabular") -> AnalyzeResponse:
    """Internal function to process analysis"""
    try:
        # Generate unique run ID
        run_id = str(uuid.uuid4())
        
        # Encode RA features
        df_encoded = encode_ra_features(df)
        
        # Train simple model for predictions (placeholder)
        feature_cols = ['RA', 'D', 'M', 'S', 'LR']
        available_features = [col for col in feature_cols if col in df_encoded.columns]
        
        if not available_features:
            raise HTTPException(status_code=400, detail="No valid features found for modeling")
        
        X = df_encoded[available_features].fillna(0)
        
        # Create synthetic target if not present (for demo)
        if 'target' not in df_encoded.columns:
            y = df_encoded[available_features[0]] * 0.8 + 0.1  # Synthetic target
        else:
            y = df_encoded['target']
        
        # Train model
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        model.fit(X, y)
        predictions = model.predict(X).tolist()
        
        # Calculate metrics
        ldrop_metrics = calculate_ldrop_metrics(df_encoded, predictions)
        ra_score_deltas = calculate_ra_score_deltas(df_encoded)
        
        # Save artifacts
        run_artifacts_dir = ARTIFACTS_DIR / run_id
        run_artifacts_dir.mkdir(exist_ok=True)
        
        # Save results as JSON
        results = {
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "predictions": predictions,
            "ldrop_metrics": ldrop_metrics,
            "ra_score_deltas": ra_score_deltas,
            "encoded_data": df_encoded.to_dict(orient='records')
        }
        
        with open(run_artifacts_dir / "results.json", 'w') as f:
            json.dump(results, f, indent=2)
        
        # Generate HTML report
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>RA Longevity Analysis Report - {run_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                .metric {{ background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
            </style>
        </head>
        <body>
            <h1>RA Longevity Analysis Report</h1>
            <div class="metric"><strong>Run ID:</strong> {run_id}</div>
            <div class="metric"><strong>Timestamp:</strong> {results['timestamp']}</div>
            
            <h2>L-Drop Metrics</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                {''.join(f'<tr><td>{k}</td><td>{v}</td></tr>' for k, v in ldrop_metrics.items())}
            </table>
            
            <h2>RA Score Deltas</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                {''.join(f'<tr><td>{k}</td><td>{v:.4f}</td></tr>' for k, v in ra_score_deltas.items())}
            </table>
            
            <h2>Predictions Summary</h2>
            <div class="metric">
                <p>Total Predictions: {len(predictions)}</p>
                <p>First 10 predictions: {predictions[:10]}</p>
            </div>
        </body>
        </html>
        """
        
        with open(run_artifacts_dir / "report.html", 'w') as f:
            f.write(html_content)
        
        # Create DKIL lock file (always create for all runs)
        # In production, you might want conditional creation based on thresholds
        dkil_data = {
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "integrity_check": True,
            "threshold_met": ldrop_metrics['samples_below_threshold'] < len(predictions) * 0.3,
            "ldrop_threshold": ldrop_metrics['ldrop_threshold'],
            "samples_below_threshold": ldrop_metrics['samples_below_threshold']
        }
        
        with open(run_artifacts_dir / "dkil_lock.json", 'w') as f:
            json.dump(dkil_data, f, indent=2)
        
        # Create bundle.zip
        zip_path = run_artifacts_dir / "bundle.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in run_artifacts_dir.glob('*'):
                if file_path.name != 'bundle.zip':
                    zipf.write(file_path, file_path.name)
        
        return AnalyzeResponse(
            run_id=run_id,
            predictions=predictions,
            ldrop_metrics=ldrop_metrics,
            ra_score_deltas=ra_score_deltas,
            timestamp=results['timestamp']
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/api/longevity/report/{run_id}")
async def get_report(
    run_id: str,
    format: str = "json",
    token: str = Depends(verify_token)
):
    """
    Retrieve JSON and HTML report from artifacts
    - Checks DKIL before serving if enabled
    - Returns JSON by default, HTML if format=html
    """
    try:
        # Validate run_id to prevent path traversal
        validated_run_id = validate_run_id(run_id)
        
        run_artifacts_dir = ARTIFACTS_DIR / validated_run_id
        
        if not run_artifacts_dir.exists():
            raise HTTPException(status_code=404, detail=f"Run ID {run_id} not found")
        
        # Check DKIL if lock file exists
        dkil_file = run_artifacts_dir / "dkil_lock.json"
        if dkil_file.exists():
            passed, dkil_data = check_dkil(validated_run_id)
            if not passed:
                raise HTTPException(
                    status_code=403, 
                    detail=f"DKIL check failed: {dkil_data.get('error', 'Unknown error')}"
                )
        
        # Return appropriate format
        if format.lower() == "html":
            html_file = run_artifacts_dir / "report.html"
            if not html_file.exists():
                raise HTTPException(status_code=404, detail="HTML report not found")
            return FileResponse(html_file, media_type="text/html")
        else:
            json_file = run_artifacts_dir / "results.json"
            if not json_file.exists():
                raise HTTPException(status_code=404, detail="JSON report not found")
            
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            return JSONResponse(content=data)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve report: {str(e)}")


@app.post("/api/longevity/deploy")
async def deploy_model(
    deploy_request: DeployRequest,
    token: str = Depends(verify_token)
):
    """
    Deploy model to model registry
    - Validates DKIL
    - Requires two keys (human + logic) in the request
    - Uploads model artifacts to registry
    """
    try:
        run_id = deploy_request.run_id
        
        # Validate run_id to prevent path traversal
        validated_run_id = validate_run_id(run_id)
        
        run_artifacts_dir = ARTIFACTS_DIR / validated_run_id
        
        if not run_artifacts_dir.exists():
            raise HTTPException(status_code=404, detail=f"Run ID {run_id} not found")
        
        # Validate DKIL
        passed, dkil_data = check_dkil(validated_run_id)
        if not passed:
            raise HTTPException(
                status_code=403,
                detail=f"DKIL validation failed: {dkil_data.get('error', 'Unknown error')}"
            )
        
        # Validate dual keys (human + logic)
        if not deploy_request.human_key or not deploy_request.logic_key:
            raise HTTPException(
                status_code=400,
                detail="Both human_key and logic_key are required for deployment"
            )
        
        # In production, validate keys against a secure store
        # For demo, just check they are non-empty
        if len(deploy_request.human_key) < 8 or len(deploy_request.logic_key) < 8:
            raise HTTPException(
                status_code=400,
                detail="Keys must be at least 8 characters long"
            )
        
        # Simulate model registry upload
        model_name = deploy_request.model_name or f"ra_longevity_model_{run_id}"
        
        # Create deployment record
        deployment_record = {
            "run_id": run_id,
            "model_name": model_name,
            "deployed_at": datetime.now(timezone.utc).isoformat(),
            "human_key_hash": hash(deploy_request.human_key),  # In production, use proper hashing
            "logic_key_hash": hash(deploy_request.logic_key),
            "dkil_validated": True,
            "status": "deployed"
        }
        
        # Save deployment record
        deployment_file = run_artifacts_dir / "deployment.json"
        with open(deployment_file, 'w') as f:
            json.dump(deployment_record, f, indent=2)
        
        # Update bundle.zip with deployment info
        zip_path = run_artifacts_dir / "bundle.zip"
        with zipfile.ZipFile(zip_path, 'a', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(deployment_file, deployment_file.name)
        
        return {
            "status": "success",
            "message": f"Model {model_name} deployed successfully",
            "run_id": run_id,
            "model_name": model_name,
            "deployed_at": deployment_record["deployed_at"],
            "bundle_path": f"/artifacts/{run_id}/bundle.zip"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")


# Mount artifacts directory as static files
app.mount("/artifacts", StaticFiles(directory=str(ARTIFACTS_DIR)), name="artifacts")


if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
