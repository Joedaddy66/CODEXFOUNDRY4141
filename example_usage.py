#!/usr/bin/env python3
"""
Example usage of the RA Longevity MLOps API

This script demonstrates how to:
1. Analyze data (JSON or CSV)
2. Retrieve reports
3. Deploy models with DKIL validation
"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000"
API_TOKEN = "demo-token-replace-in-production"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}


def analyze_json_data():
    """Example: Analyze JSON data"""
    print("=" * 60)
    print("Example 1: Analyze JSON Data")
    print("=" * 60)
    
    data = {
        "data": [
            {"value": 10, "metric": 20},
            {"value": 15, "metric": 25},
            {"value": 20, "metric": 30},
            {"value": 25, "metric": 35},
            {"value": 30, "metric": 40},
            {"value": 35, "metric": 45},
            {"value": 40, "metric": 50},
        ],
        "mode": "tabular"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/longevity/analyze",
        headers=HEADERS,
        json=data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Analysis successful!")
        print(f"  Run ID: {result['run_id']}")
        print(f"  Predictions: {result['predictions'][:3]}... (showing first 3)")
        print(f"  L-drop Mean: {result['ldrop_metrics']['mean_prediction']:.4f}")
        print(f"  RA Score Mean: {result['ra_score_deltas']['ra_mean']:.4f}")
        return result['run_id']
    else:
        print(f"✗ Analysis failed: {response.text}")
        return None


def analyze_csv_file(filepath="example_data.csv"):
    """Example: Analyze CSV file"""
    print("\n" + "=" * 60)
    print("Example 2: Analyze CSV File")
    print("=" * 60)
    
    try:
        with open(filepath, 'rb') as f:
            files = {"file": (filepath, f, "text/csv")}
            response = requests.post(
                f"{BASE_URL}/api/longevity/analyze/csv",
                headers=HEADERS,
                files=files
            )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ CSV analysis successful!")
            print(f"  Run ID: {result['run_id']}")
            print(f"  Number of predictions: {len(result['predictions'])}")
            return result['run_id']
        else:
            print(f"✗ CSV analysis failed: {response.text}")
            return None
    except FileNotFoundError:
        print(f"✗ File not found: {filepath}")
        return None


def get_json_report(run_id):
    """Example: Get JSON report"""
    print("\n" + "=" * 60)
    print("Example 3: Retrieve JSON Report")
    print("=" * 60)
    
    response = requests.get(
        f"{BASE_URL}/api/longevity/report/{run_id}",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        print(f"✓ JSON report retrieved successfully!")
        result = response.json()
        print(f"  Timestamp: {result['timestamp']}")
        print(f"  L-drop samples below threshold: {result['ldrop_metrics']['samples_below_threshold']}")
    else:
        print(f"✗ Failed to get report: {response.text}")


def get_html_report(run_id):
    """Example: Get HTML report"""
    print("\n" + "=" * 60)
    print("Example 4: Retrieve HTML Report")
    print("=" * 60)
    
    response = requests.get(
        f"{BASE_URL}/api/longevity/report/{run_id}?format=html",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        print(f"✓ HTML report retrieved successfully!")
        print(f"  Content length: {len(response.content)} bytes")
        print(f"  You can view it at: {BASE_URL}/artifacts/{run_id}/report.html")
    else:
        print(f"✗ Failed to get HTML report: {response.text}")


def deploy_model(run_id):
    """Example: Deploy model with DKIL validation"""
    print("\n" + "=" * 60)
    print("Example 5: Deploy Model")
    print("=" * 60)
    
    deploy_data = {
        "run_id": run_id,
        "human_key": "human-approval-key-12345678",
        "logic_key": "logic-validation-key-87654321",
        "model_name": "ra_longevity_example_v1"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/longevity/deploy",
        headers=HEADERS,
        json=deploy_data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Model deployed successfully!")
        print(f"  Model name: {result['model_name']}")
        print(f"  Deployed at: {result['deployed_at']}")
        print(f"  Bundle path: {result['bundle_path']}")
    else:
        print(f"✗ Deployment failed: {response.text}")


def download_bundle(run_id):
    """Example: Download artifact bundle"""
    print("\n" + "=" * 60)
    print("Example 6: Download Artifact Bundle")
    print("=" * 60)
    
    response = requests.get(
        f"{BASE_URL}/artifacts/{run_id}/bundle.zip",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        filename = f"bundle_{run_id[:8]}.zip"
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"✓ Bundle downloaded successfully!")
        print(f"  Saved to: {filename}")
    else:
        print(f"✗ Failed to download bundle: {response.status_code}")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("RA Longevity MLOps API - Example Usage")
    print("=" * 60)
    print(f"API URL: {BASE_URL}")
    print(f"Token: {'*' * 20}...")  # Masked for security
    
    # Check if server is running
    try:
        response = requests.get(BASE_URL)
        if response.status_code != 200:
            print("\n✗ Error: Server is not responding properly")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Cannot connect to server")
        print(f"  Make sure the server is running at {BASE_URL}")
        print("  Start it with: python main.py")
        sys.exit(1)
    
    # Run examples
    run_id = analyze_json_data()
    if not run_id:
        print("\n✗ Stopping due to analysis failure")
        sys.exit(1)
    
    get_json_report(run_id)
    get_html_report(run_id)
    deploy_model(run_id)
    download_bundle(run_id)
    
    # Optional: Try CSV analysis
    csv_run_id = analyze_csv_file()
    
    print("\n" + "=" * 60)
    print("✓ All examples completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print(f"  - View HTML report: {BASE_URL}/artifacts/{run_id}/report.html")
    print(f"  - View JSON report: {BASE_URL}/api/longevity/report/{run_id}")
    print(f"  - Download bundle: {BASE_URL}/artifacts/{run_id}/bundle.zip")
    print("\nAPI Documentation:")
    print(f"  - Interactive docs: {BASE_URL}/docs")
    print(f"  - ReDoc: {BASE_URL}/redoc")


if __name__ == "__main__":
    main()
