import pytest
from fastapi.testclient import TestClient

def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["ml_engine"] == "loaded"

def test_get_locations(client: TestClient):
    response = client.get("/api/locations")
    assert response.status_code == 200
    locations = response.json()
    assert len(locations) >= 16
    # Verify North East states are present
    states = {loc["state"] for loc in locations}
    assert "Assam" in states
    assert "Meghalaya" in states
    assert "Mizoram" in states
    assert "Sikkim" in states

def test_get_location_by_id(client: TestClient):
    response = client.get("/api/locations/LOC-AS-01")
    assert response.status_code == 200
    loc = response.json()
    assert loc["location_id"] == "LOC-AS-01"
    assert loc["state"] == "Assam"

def test_create_location(client: TestClient):
    new_loc = {
        "location_id": "LOC-TEST-01",
        "name": "Test Ridge",
        "state": "Assam",
        "district": "Karbi Anglong",
        "latitude": 25.8,
        "longitude": 93.4,
        "elevation": 550.0,
        "slope": 33.0,
        "aspect": "S",
        "terrain_roughness": 20.0,
        "geology_type": "Gneissic Complex",
        "vegetation_type": "Deciduous Forest",
        "monitoring_status": "ACTIVE"
    }
    response = client.post("/api/locations", json=new_loc)
    assert response.status_code == 201
    created = response.json()
    assert created["location_id"] == "LOC-TEST-01"

def test_predict_endpoint_valid(client: TestClient):
    payload = {
        "location_id": "LOC-AS-01",
        "latitude": 26.1664,
        "longitude": 91.7051,
        "rainfall_1h": 22.0,
        "rainfall_24h": 140.0,
        "rainfall_7d": 380.0,
        "soil_moisture": 90.0,
        "slope": 35.0,
        "elevation": 210.0,
        "terrain_roughness": 18.0,
        "vegetation_index": 0.5
    }
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["location_id"] == "LOC-AS-01"
    assert "risk_score" in res
    assert res["risk_level"] in ["HIGH", "SEVERE"]
    assert "recommendation" in res
    assert "explanation" in res
    assert len(res["risk_factors"]) > 0

def test_predict_endpoint_validation_error(client: TestClient):
    invalid_payload = {
        "location_id": "LOC-ERR",
        "latitude": 26.1,
        "longitude": 91.7,
        "rainfall_1h": -5.0,  # Invalid negative rainfall
        "rainfall_24h": 100.0,
        "rainfall_7d": 200.0,
        "soil_moisture": 150.0, # Invalid moisture > 100
        "slope": 45.0,
        "elevation": 300.0,
        "terrain_roughness": 10.0,
        "vegetation_index": 0.5
    }
    response = client.post("/api/predict", json=invalid_payload)
    assert response.status_code == 422

def test_get_alerts_and_acknowledge(client: TestClient):
    # First generate a high hazard prediction to guarantee an alert exists
    payload = {
        "location_id": "LOC-ML-01",
        "latitude": 25.2986,
        "longitude": 91.7322,
        "rainfall_1h": 35.0,
        "rainfall_24h": 200.0,
        "rainfall_7d": 500.0,
        "soil_moisture": 96.0,
        "slope": 45.0,
        "elevation": 1430.0,
        "terrain_roughness": 40.0,
        "vegetation_index": 0.3
    }
    client.post("/api/predict", json=payload)

    alerts_res = client.get("/api/alerts")
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()
    assert len(alerts) > 0

    target_alert = alerts[0]
    alert_id = target_alert["alert_id"]

    # Test acknowledge
    ack_res = client.put(f"/api/alerts/{alert_id}/acknowledge", json={"acknowledged_by": "COMMANDER_DUTY"})
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "ACKNOWLEDGED"

    # Test resolve
    res_res = client.put(f"/api/alerts/{alert_id}/resolve", json={"resolved_by": "FIELD_OFFICER", "resolution_notes": "Drainage cleared"})
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "RESOLVED"

def test_threshold_settings_update(client: TestClient):
    # Get current thresholds
    get_res = client.get("/api/settings/thresholds")
    assert get_res.status_code == 200
    
    # Update thresholds
    update_res = client.put("/api/settings/thresholds", json={
        "threshold_low": 20.0,
        "threshold_moderate": 45.0,
        "threshold_high": 70.0,
        "updated_by": "TEST_ADMIN"
    })
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["threshold_low"] == 20.0
    assert updated["threshold_moderate"] == 45.0
    assert updated["threshold_high"] == 70.0

def test_historical_analysis(client: TestClient):
    response = client.get("/api/analysis/historical")
    assert response.status_code == 200
    events = response.json()
    assert len(events) >= 8
    event_names = [e["location_name"] for e in events]
    assert any("Tupul" in name for name in event_names)
    assert any("Haflong" in name for name in event_names)

def test_trends_analysis(client: TestClient):
    response = client.get("/api/analysis/trends")
    assert response.status_code == 200
    data = response.json()
    assert "timeseries" in data
    assert "state_breakdown" in data
