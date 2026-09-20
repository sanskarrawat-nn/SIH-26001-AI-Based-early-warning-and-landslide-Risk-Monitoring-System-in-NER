# Database Specification: AI-Based early warning and landslide Risk Monitoring System in NER

## 1. Overview & Dual Database Architecture

The persistence layer uses **SQLAlchemy 2.0 ORM** supporting both:
- **SQLite (Zero-Config Development):** Out-of-the-box local development and automated CI testing.
- **PostgreSQL 16 (Production / Cloud):** High-concurrency ACID transactions, connection pooling, and JSON storage for Docker and Render.

---

## 2. Entity-Relationship Schema

```mermaid
erDiagram
    LOCATIONS ||--o{ ENVIRONMENTAL_MEASUREMENTS : records
    LOCATIONS ||--o{ PREDICTIONS : produces
    LOCATIONS ||--o{ ALERTS : triggers

    LOCATIONS {
        string location_id PK
        string name
        string state
        string district
        float latitude
        float longitude
        float elevation
        float slope
        string aspect
        float terrain_roughness
        string geology_type
        string monitoring_status
        string risk_level
        float current_risk_score
        string alert_status
        json latest_measurements
        json latest_prediction
        datetime created_at
        datetime updated_at
    }

    ENVIRONMENTAL_MEASUREMENTS {
        int id PK
        string location_id FK
        datetime timestamp
        float rainfall_1h
        float rainfall_24h
        float rainfall_7d
        float soil_moisture
        float soil_saturation
        float vegetation_index
        string source
        json raw_payload
    }

    PREDICTIONS {
        int id PK
        string location_id FK
        datetime timestamp
        float risk_score
        string risk_level
        float probability
        float confidence
        json risk_factors
        text recommendation
        text explanation
        json input_features
        string model_version
    }

    ALERTS {
        int id PK
        string alert_id UK
        string location_id FK
        string severity
        string status
        float risk_score
        string title
        text message
        json triggering_factors
        text recommended_action
        json sop_actions
        datetime created_at
        datetime acknowledged_at
        string acknowledged_by
        datetime resolved_at
        string resolved_by
        text resolution_notes
    }

    HISTORICAL_LANDSLIDES {
        int id PK
        string event_id UK
        string location_name
        string state
        string district
        float latitude
        float longitude
        datetime event_date
        string severity
        float triggering_rainfall_24h
        float triggering_rainfall_7d
        float slope
        float elevation
        int casualties
        text infrastructure_damage
        string data_source
    }

    SYSTEM_SETTINGS {
        int id PK
        string key UK
        float threshold_low
        float threshold_moderate
        float threshold_high
        datetime updated_at
        string updated_by
    }
```

---

## 3. Pre-Seeded Datasets

Upon first startup, the system automatically checks if tables are empty and executes `app.database.seed_data.seed_database()`:
- **16 High-Risk North Eastern Sites:** Representing all 8 states (Guwahati, Haflong, Cherrapunji, Shillong, Aizawl, Champhai, Kohima, Mokokchung, Tupul Noney, Imphal, Itanagar, Tawang, Gangtok, Mangan, Dharmanagar, Belonia).
- **8 Major GSI Historical Disasters:** Complete with casualty figures, triggering rainfall, and geological fault line data.
- **Default Operational Hazard Boundaries:** LOW < 25, MODERATE 25–50, HIGH 50–75, SEVERE > 75.
