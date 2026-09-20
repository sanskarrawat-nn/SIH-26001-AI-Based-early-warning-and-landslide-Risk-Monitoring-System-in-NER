# System Architecture: AI-Based early warning and landslide Risk Monitoring System in NER

## 1. Architectural Overview

The NER-LEWS architecture is built as an event-driven, decoupled, multi-tier system tailored for high-concurrency crisis command centers.

```
+-------------------------------------------------------------------------+
|                       FRONTEND COMMAND CENTER                           |
|       (React 18 + TypeScript + Vite + Tailwind CSS + Leaflet GIS)       |
+-------------------------------------------------------------------------+
                                    |
                           REST APIs & JSON
                                    |
                                    v
+-------------------------------------------------------------------------+
|                        BACKEND CORE (FastAPI)                           |
|                                                                         |
|  +-------------------+  +-------------------+  +---------------------+  |
|  | Location Services |  | Prediction Engine |  | Early Warning Engine|  |
|  +-------------------+  +-------------------+  +---------------------+  |
|            |                      |                       |             |
|            v                      v                       v             |
|  +-------------------+  +-------------------+  +---------------------+  |
|  | Dynamic Weather   |  | Physics Feature   |  | Configurable        |  |
|  | Providers Layer   |  | Engineering       |  | Threshold Manager   |  |
|  +-------------------+  +-------------------+  +---------------------+  |
|            |                      |                       |             |
|            v                      v                       v             |
|  +-------------------+  +-------------------+  +---------------------+  |
|  | Open-Meteo & SIM  |  | Calibrated Random |  | SOP Checklist &     |  |
|  | Telemetry Feeds   |  | Forest Ensemble   |  | Alert Dispatches    |  |
|  +-------------------+  +-------------------+  +---------------------+  |
+-------------------------------------------------------------------------+
                                    |
                           SQLAlchemy 2.0 ORM
                                    |
                                    v
+-------------------------------------------------------------------------+
|                  PERSISTENCE LAYER (PostgreSQL / SQLite)                |
|  Locations | Environmental | Predictions | Alerts | Historical | Config |
+-------------------------------------------------------------------------+
```

---

## 2. Geotechnical Physical Foundations

Landslides in the North Eastern Himalayas are governed by limit equilibrium mechanics. The system models the **Mohr-Coulomb Failure Criterion**:

$$\tau_f = c' + (\sigma_n - u) \tan \phi'$$

Where:
- $\tau_f$: Shear strength along the slip surface.
- $c'$: Effective soil/rock cohesion (reinforced by vegetation root tensile strength modeled via NDVI).
- $\sigma_n$: Total normal stress due to overburden soil column weight ($\gamma \cdot z \cdot \cos^2 \theta$).
- $u$: Pore-water pressure induced by soil saturation ($u = \gamma_w \cdot h_w \cdot \cos^2 \theta$).
- $\phi'$: Angle of internal friction for weathered residual flysch sediments.

When antecedent precipitation $R_{7d}$ and intense daily rainfall $R_{24h}$ infiltrate, soil saturation $S_r \to 1.0$, pore-water pressure $u$ increases, driving the effective normal stress $\sigma' = \sigma_n - u$ towards zero. Gravitational shear stress $\tau_{drive} \propto \sin \theta \cdot \cos \theta$ overtakes $\tau_f$, precipitating slope failure.

---

## 3. Data Ingestion & Abstraction Layer

The system separates data acquisition from business logic through the `BaseEnvironmentalProvider` interface:

1. `OpenMeteoProvider`: Communicates with external meteorological satellites and numeric weather models to fetch hourly precipitation, surface pressure, and soil moisture at specified coordinates.
2. `SimulatedSensorProvider`: Realistic stochastic physical simulator that models diurnal orographic precipitation and monsoon cloudbursts in the Brahmaputra-Barak basins.
3. `HybridEnvironmentalProvider`: Attempts live API queries with a 3.5s timeout and automatically fails over to the simulator if external internet connectivity is restricted or throttled.

---

## 4. Machine Learning Pipeline

1. **Feature Engineering:**
   - Antecedent Rainfall Index (ARI): $ARI = R_{24h} + 0.75 \times \frac{R_{7d} - R_{24h}}{6}$
   - Critical Rainfall Threshold Ratio: Compares $R_{24h}$ against the Himalayan Intensity-Duration curve ($I_{crit} = \alpha D^{-\beta}$).
   - Slope-Rainfall Interaction: $\frac{\theta \times R_{24h}}{100}$
   - Pore-Water Destabilization Index: $\frac{S_r \cdot \tan\theta}{\text{Root Cohesion}}$
2. **Classifier:**
   - 160-estimator Balanced Random Forest with max depth 12.
   - Platt Sigmoid Calibration (`CalibratedClassifierCV`) ensuring probabilities $P(Y=1|X)$ represent genuine empirical frequencies.
3. **Attribution Engine:**
   - Computes normalized feature z-scores scaled by base estimator feature importances.
   - Generates contextual natural language narratives explaining which physical triggers dominated the prediction.

---

## 5. Early Warning & Threshold Loop

Predictions automatically feed into the `AlertEngine`. If the risk score breaches the active threshold:
- `risk_score >= threshold_high` (default 75): **SEVERE** alert generated; status set to `CRITICAL`.
- `risk_score >= threshold_moderate` (default 50): **HIGH** alert generated; status set to `WARNING`.
- Formulates Standard Operating Procedure (SOP) action items (e.g. Traffic halts on NH-29, NDRF pre-positioning, DDMA shelter opening).
