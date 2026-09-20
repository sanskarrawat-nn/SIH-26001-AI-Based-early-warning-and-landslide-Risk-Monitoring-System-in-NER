# Testing & Verification Guide: AI-Based early warning and landslide Risk Monitoring System in NER

## 1. Test Suite Summary

The project includes automated backend unit and integration tests and strict frontend TypeScript compilation verification.

### Backend Test Coverage (Pytest)
- `test_health_check`: Validates `/health` system diagnostics.
- `test_get_locations`: Validates 16 North Eastern locations seeded across all 8 states.
- `test_get_location_by_id`: Validates location retrieval by ID.
- `test_create_location`: Validates dynamic location registration.
- `test_predict_endpoint_valid`: Validates `POST /api/predict` feature ingestion, ML inference, and alert triggering.
- `test_predict_endpoint_validation_error`: Tests Pydantic input range validation for invalid negative rainfall or moisture $> 100\%$.
- `test_get_alerts_and_acknowledge`: Tests full early warning lifecycle: trigger $\to$ dispatch $\to$ acknowledge $\to$ resolve.
- `test_threshold_settings_update`: Tests dynamic threshold reconfiguration without restart.
- `test_historical_analysis`: Tests GSI catalog records retrieval.
- `test_trends_analysis`: Tests multi-location time-series correlation.
- `test_feature_engineering`: Validates geotechnical derivations (ARI, pore-pressure index, critical rainfall ratio).
- `test_predict_landslide_risk_severe`: Tests severe hazard trigger under extreme meteorological conditions.
- `test_predict_landslide_risk_low`: Tests low hazard output under dry/stable conditions.
- `test_model_metadata`: Verifies model ROC-AUC $\ge 0.95$ and F1 $\ge 0.90$.

---

## 2. Running Automated Tests

### Backend Tests:
```bash
cd backend
source venv/bin/activate
python -m pytest tests/ -v
```

Expected Output:
```
============================== 14 passed in 1.89s ==============================
```

### Frontend TypeScript Verification & Production Build:
```bash
cd frontend
npm run build
```

Expected Output:
```
✓ 2235 modules transformed.
✓ built in 1.48s
```
