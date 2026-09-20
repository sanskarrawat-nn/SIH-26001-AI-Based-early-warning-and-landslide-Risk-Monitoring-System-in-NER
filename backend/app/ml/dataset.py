import numpy as np
import pandas as pd
from app.ml.feature_engineering import engineer_features, FEATURE_COLUMNS

def generate_ner_landslide_dataset(n_samples: int = 2400, random_seed: int = 42) -> pd.DataFrame:
    """
    Generates a scientifically grounded, physics-informed synthetic dataset
    modeling geotechnical landslide triggering in the North Eastern Himalayan Region.
    """
    np.random.seed(random_seed)

    # 1. Topographic features
    # Slopes in NER: plains (5-15°), rolling hills (15-28°), steep escarpments (28-55°)
    slope = np.concatenate([
        np.random.uniform(5, 20, int(n_samples * 0.25)),
        np.random.uniform(20, 35, int(n_samples * 0.40)),
        np.random.uniform(35, 58, int(n_samples * 0.35))
    ])
    np.random.shuffle(slope)

    elevation = np.random.uniform(100, 3800, n_samples)
    terrain_roughness = np.random.uniform(5, 45, n_samples) + (slope * 0.4)
    vegetation_index = np.clip(np.random.normal(0.60, 0.22, n_samples), -0.1, 0.95)

    # 2. Meteorological features (North East Monsoon & Dry season profiles)
    # 40% dry/mild conditions, 40% moderate monsoon, 20% extreme cloudburst/torrential
    regime = np.random.choice(["dry", "monsoon", "extreme"], size=n_samples, p=[0.40, 0.40, 0.20])

    rainfall_1h = np.zeros(n_samples)
    rainfall_24h = np.zeros(n_samples)
    rainfall_7d = np.zeros(n_samples)
    soil_moisture = np.zeros(n_samples)

    for i in range(n_samples):
        if regime[i] == "dry":
            r24 = np.random.exponential(scale=6.0)
            r1 = min(r24, np.random.exponential(scale=2.0))
            r7 = r24 + np.random.uniform(5, 30)
            sm = np.clip(np.random.normal(25, 10), 5, 55)
        elif regime[i] == "monsoon":
            r24 = np.random.uniform(25, 95)
            r1 = min(r24, np.random.uniform(2, 18))
            r7 = r24 + np.random.uniform(70, 240)
            sm = np.clip(np.random.normal(68, 12), 40, 92)
        else: # extreme cloudburst / persistent multi-day deluge
            r24 = np.random.uniform(90, 320)
            r1 = min(r24, np.random.uniform(15, 65))
            r7 = r24 + np.random.uniform(180, 500)
            sm = np.clip(np.random.normal(86, 7), 65, 99)

        rainfall_1h[i] = round(r1, 1)
        rainfall_24h[i] = round(r24, 1)
        rainfall_7d[i] = round(r7, 1)
        soil_moisture[i] = round(sm, 1)

    # Compile raw records
    raw_records = []
    for i in range(n_samples):
        rec = {
            "rainfall_1h": rainfall_1h[i],
            "rainfall_24h": rainfall_24h[i],
            "rainfall_7d": rainfall_7d[i],
            "soil_moisture": soil_moisture[i],
            "slope": round(float(slope[i]), 1),
            "elevation": round(float(elevation[i]), 1),
            "terrain_roughness": round(float(terrain_roughness[i]), 1),
            "vegetation_index": round(float(vegetation_index[i]), 2),
        }
        features = engineer_features(rec)

        # Physics-informed Ground Truth Labeling:
        # Mohr-Coulomb Factor of Safety proxy:
        # FS = (Cohesion + (sigma - u) * tan(phi)) / (shear_stress)
        # Landslide occurs when FS < 1.0 (approximate threshold)
        crit_ratio = features["critical_rainfall_ratio"]
        pore_idx = features["pore_pressure_index"]
        slope_val = features["slope"]
        sm_val = features["soil_moisture"]
        r24_val = features["rainfall_24h"]

        # Driving instability score (higher = unstable)
        instability_score = (
            (crit_ratio * 0.38) +
            (pore_idx * 0.28) +
            ((slope_val / 55.0) * 0.22) +
            ((sm_val / 100.0) * 0.18) +
            (features["hourly_intensity_surge"] * 0.08) -
            (features["vegetation_index"] * 0.15)
        )
        
        # Add slight natural geotechnical stochastic variance
        noise = np.random.normal(0, 0.06)
        prob = 1.0 / (1.0 + np.exp(-6.5 * (instability_score + noise - 0.72)))
        label = 1 if prob >= 0.50 else 0

        features["landslide_occurred"] = label
        features["true_probability"] = round(float(prob), 4)
        raw_records.append(features)

    df = pd.DataFrame(raw_records)
    return df
