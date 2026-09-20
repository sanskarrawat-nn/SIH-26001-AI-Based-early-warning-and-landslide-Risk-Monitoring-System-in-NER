import math
from typing import Dict, Any
import numpy as np

def engineer_features(raw: Dict[str, float]) -> Dict[str, float]:
    """
    Transforms raw environmental & geospatial inputs into physics-informed 
    geotechnical and hydrometeorological features for landslide susceptibility prediction.
    """
    rainfall_1h = float(raw.get("rainfall_1h", 0.0))
    rainfall_24h = float(raw.get("rainfall_24h", 0.0))
    rainfall_7d = float(raw.get("rainfall_7d", 0.0))
    soil_moisture = float(raw.get("soil_moisture", 0.0))
    slope = float(raw.get("slope", 0.0))
    elevation = float(raw.get("elevation", 0.0))
    terrain_roughness = float(raw.get("terrain_roughness", 0.0))
    ndvi = float(raw.get("vegetation_index", 0.5))

    # Convert slope to radians for trigonometric stresses
    slope_rad = math.radians(slope)
    sin_slope = math.sin(slope_rad)
    cos_slope = math.cos(slope_rad)
    tan_slope = math.tan(slope_rad) if slope < 89 else 50.0

    # 1. Antecedent Rainfall Index (decayed memory of precipitation)
    antecedent_prev_days = max(0.0, rainfall_7d - rainfall_24h)
    ari = rainfall_24h + (0.75 * antecedent_prev_days / 6.0)

    # 2. Soil Saturation Index (ratio to typical field capacity in Himalayan regolith ~80%)
    soil_saturation_ratio = min(1.0, max(0.0, soil_moisture / 80.0))

    # 3. Slope - Rainfall Interaction Factor
    slope_rain_interaction = (slope * rainfall_24h) / 100.0

    # 4. Critical Intensity-Duration Himalayan Threshold (GSI / Caine empirical curve)
    # Baseline 24h critical trigger ~ 100mm, reduced on steep slopes > 30 degrees
    slope_factor = max(0.35, 1.0 - max(0.0, (slope - 25.0) / 45.0))
    r_crit_24h = 105.0 * slope_factor
    critical_rainfall_ratio = rainfall_24h / max(10.0, r_crit_24h)

    # 5. Geotechnical Shear Stress Proxy (gravitational component along failure plane)
    shear_stress_proxy = sin_slope * cos_slope

    # 6. Pore-water pressure destabilization index
    # (High soil moisture + steep slope - root cohesion from NDVI)
    root_cohesion = max(0.1, (ndvi + 0.2) * 0.8)
    pore_pressure_index = (soil_saturation_ratio * tan_slope) / root_cohesion

    # 7. Elevation relief and orographic amplification factor
    orographic_factor = min(2.0, 1.0 + (elevation / 4000.0))

    # 8. Short-term hourly cloudburst intensity surge
    hourly_intensity_surge = rainfall_1h / max(1.0, (rainfall_24h / 24.0) + 1.0)

    return {
        "rainfall_1h": rainfall_1h,
        "rainfall_24h": rainfall_24h,
        "rainfall_7d": rainfall_7d,
        "soil_moisture": soil_moisture,
        "slope": slope,
        "elevation": elevation,
        "terrain_roughness": terrain_roughness,
        "vegetation_index": ndvi,
        "antecedent_rainfall_index": ari,
        "soil_saturation_ratio": soil_saturation_ratio,
        "slope_rain_interaction": slope_rain_interaction,
        "critical_rainfall_ratio": critical_rainfall_ratio,
        "shear_stress_proxy": shear_stress_proxy,
        "pore_pressure_index": pore_pressure_index,
        "orographic_factor": orographic_factor,
        "hourly_intensity_surge": hourly_intensity_surge
    }

FEATURE_COLUMNS = [
    "rainfall_1h",
    "rainfall_24h",
    "rainfall_7d",
    "soil_moisture",
    "slope",
    "elevation",
    "terrain_roughness",
    "vegetation_index",
    "antecedent_rainfall_index",
    "soil_saturation_ratio",
    "slope_rain_interaction",
    "critical_rainfall_ratio",
    "shear_stress_proxy",
    "pore_pressure_index",
    "orographic_factor",
    "hourly_intensity_surge"
]
