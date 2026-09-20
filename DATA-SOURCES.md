# Data Sources & Geotechnical Ingestion Guide

## 1. Primary Environmental & Terrestrial Data Streams

The NER-LEWS architecture integrates 6 primary observational streams:

### 1. Rainfall Telemetry
- **Parameters:** 1-hour cloudburst intensity ($mm/h$), 24-hour cumulative ($mm$), 7-day antecedent ($mm$).
- **Live Provider:** Open-Meteo High-Resolution Numeric Weather Forecast & API.
- **Production Extension:** IMD Doppler Weather Radars (Cherrapunji, Guwahati, Agartala, Mohanbari) & Automatic Weather Station (AWS) telemetric rain-gauges.

### 2. Soil Moisture & Hydraulic State
- **Parameters:** Volumetric water content ($0–100\%$), degree of saturation ($S_r$).
- **Live Provider:** Open-Meteo / ECMWF ERA5-Land soil moisture layers ($0–7 \text{ cm}, 7–28 \text{ cm}$).
- **Physical Representation:** In-situ piezometers and Time-Domain Reflectometry (TDR) moisture probes installed along active highway slopes (e.g. NH-29 Kohima, Jatinga Dima Hasao).

### 3. Digital Elevation Model (DEM) & Topography
- **Parameters:** Elevation ($m$ a.s.l.), slope angle ($\theta \in [0, 90^\circ]$), slope aspect (N, NE, E, SE, S, SW, W, NW), terrain roughness index (TRI).
- **Baseline Source:** Shuttle Radar Topography Mission (SRTM) 30m and Cartosat-1 DEM.

### 4. Satellite Remote Sensing & Vegetation (NDVI)
- **Parameters:** Normalized Difference Vegetation Index ($\text{NDVI} \in [-0.2, 1.0]$), land-use / land-cover classification.
- **Source:** Sentinel-2 Level-2A Multi-Spectral Instrument (MSI) & Landsat-8 Operational Land Imager.
- **Geotechnical Role:** NDVI models the root tensile reinforcement and biotechnical anchoring of shallow regolith.

### 5. Historical Landslides & Geohazard Catalog
- **Source:** Geological Survey of India (GSI) National Landslide Susceptibility Mapping (NLSM), National Disaster Management Authority (NDMA), State Disaster Management Authorities (MSDMA, NSDMA, ASDMA).
- **Events Recorded:** 2022 Tupul Noney landslide, 2022 Haflong Dima Hasao railway cutoff, 2024 Melthum Aizawl quarry failure, 2023 Chungthang GLOF/debris flow, etc.

### 6. Geographic Information System (GIS)
- **Coordinates:** High-precision WGS84 decimal degrees.
- **Coverage:** Complete 8-state North Eastern Council (NEC) territorial boundary.
