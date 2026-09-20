# REST API Specification: AI-Based early warning and landslide Risk Monitoring System in NER

Base URL: `http://localhost:8000/api`  
Interactive Swagger UI: `http://localhost:8000/docs`  
ReDoc: `http://localhost:8000/redoc`

---

## 1. System Health

### `GET /health`
Returns system diagnostics, database status, ML engine state, and weather provider mode.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "AI-Based early warning and landslide Risk Monitoring System in NER",
  "version": "1.0.0",
  "database": "healthy",
  "ml_engine": "loaded",
  "weather_provider": "hybrid"
}
```

---

## 2. Landslide Risk Prediction

### `POST /api/predict`
Calculates real-time landslide risk probability, score, category, and feature attribution. Automatically triggers alerts if thresholds are exceeded.

**Request Body:**
```json
{
  "location_id": "LOC-AS-02",
  "latitude": 25.1783,
  "longitude": 93.0250,
  "rainfall_1h": 22.0,
  "rainfall_24h": 145.0,
  "rainfall_7d": 380.0,
  "soil_moisture": 91.5,
  "slope": 41.0,
  "elevation": 680.0,
  "terrain_roughness": 34.0,
  "vegetation_index": 0.48
}
```

**Response (200 OK):**
```json
{
  "location_id": "LOC-AS-02",
  "risk_score": 98.7,
  "risk_level": "SEVERE",
  "probability": 0.987,
  "confidence": 0.985,
  "risk_factors": [
    {
      "factor": "24-Hour Rainfall",
      "impact": "CRITICAL",
      "weight": 0.412,
      "description": "Cumulative 24h precipitation volume (145.0 mm in 24h (severely elevated))"
    },
    {
      "factor": "Soil Moisture Saturation",
      "impact": "CRITICAL",
      "weight": 0.324,
      "description": "High pore-water pressure reducing shear strength (91.5% volumetric moisture content (approaching saturation))"
    }
  ],
  "timestamp": "2026-09-05T10:45:00Z",
  "recommendation": "CRITICAL ALERT: Issue immediate evacuation orders for downstream settlements...",
  "explanation": "CRITICAL INSTABILITY DETECTED: Risk is categorized as SEVERE (98.7/100)..."
}
```

---

## 3. Location Management

### `GET /api/locations`
List all monitored locations.
- Query parameters: `state`, `district`, `risk_level`, `monitoring_status`

### `GET /api/locations/{id}`
Retrieve profile and latest telemetry for a single location.

### `POST /api/locations`
Register a new monitored hill sector.

### `PUT /api/locations/{id}`
Update attributes for a location.

### `DELETE /api/locations/{id}`
Delete a location from monitoring.

### `POST /api/locations/{id}/sync`
Poll live telemetry from the Environmental Data Provider and update model state.

---

## 4. Early Warnings & Alerts

### `GET /api/alerts`
Retrieve generated alerts.
- Query parameters: `severity` (SEVERE, HIGH, MODERATE), `status` (ACTIVE, ACKNOWLEDGED, RESOLVED), `location_id`

### `PUT /api/alerts/{id}/acknowledge`
Acknowledge an active early warning by responder name/callsign.

### `PUT /api/alerts/{id}/resolve`
Resolve an alert with field clearance notes.

---

## 5. Historical Analysis & Trends

### `GET /api/analysis/historical`
Retrieve catalog of North Eastern landslide disasters (GSI/NDMA).

### `GET /api/analysis/trends`
Get time-series correlation between precipitation and predicted risk scores.

### `GET /api/analysis/model-performance`
Get ML evaluation metrics (accuracy, precision, recall, F1, ROC-AUC, confusion matrix, feature weights).

---

## 6. Threshold Settings

### `GET /api/settings/thresholds`
Retrieve active operational hazard score boundaries.

### `PUT /api/settings/thresholds`
Update operational hazard score boundaries dynamically without restart.
