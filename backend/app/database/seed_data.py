from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.location import Location
from app.models.historical import HistoricalLandslide
from app.models.settings import SystemSettings
from app.models.prediction import Prediction
from app.models.alert import Alert
from app.ml.pipeline import predict_landslide_risk
from app.services.explanation_engine import generate_geotechnical_explanation, generate_recommendations

def utc_now():
    return datetime.now(timezone.utc)

NER_LOCATIONS = [
    {
        "location_id": "LOC-AS-01",
        "name": "Kamakhya / Nilachal Hills",
        "state": "Assam",
        "district": "Kamrup Metropolitan (Guwahati)",
        "latitude": 26.1664,
        "longitude": 91.7051,
        "elevation": 210.0,
        "slope": 32.5,
        "aspect": "NW",
        "terrain_roughness": 18.0,
        "geology_type": "Precambrian Granite Gneiss with thick saprolite mantle",
        "vegetation_type": "Mixed Moist Deciduous Forest",
        "rainfall_1h": 4.5,
        "rainfall_24h": 42.0,
        "rainfall_7d": 115.0,
        "soil_moisture": 58.0,
        "vegetation_index": 0.62
    },
    {
        "location_id": "LOC-AS-02",
        "name": "Haflong - Jatinga Hill Corridor",
        "state": "Assam",
        "district": "Dima Hasao",
        "latitude": 25.1783,
        "longitude": 93.0250,
        "elevation": 680.0,
        "slope": 41.0,
        "aspect": "SE",
        "terrain_roughness": 34.0,
        "geology_type": "Disang & Barail Shales, highly fractured flysch sediments",
        "vegetation_type": "Semi-evergreen bamboo forest",
        "rainfall_1h": 22.0,
        "rainfall_24h": 145.0,
        "rainfall_7d": 380.0,
        "soil_moisture": 91.5,
        "vegetation_index": 0.48
    },
    {
        "location_id": "LOC-ML-01",
        "name": "Sohra (Cherrapunji) - Mawkdok Valley",
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "latitude": 25.2986,
        "longitude": 91.7322,
        "elevation": 1430.0,
        "slope": 44.5,
        "aspect": "S",
        "terrain_roughness": 42.0,
        "geology_type": "Cretaceous-Tertiary Sandstone overlying Precambrian Gneiss",
        "vegetation_type": "Subtropical Grassland & Cliff Shrub",
        "rainfall_1h": 28.0,
        "rainfall_24h": 168.0,
        "rainfall_7d": 490.0,
        "soil_moisture": 94.0,
        "vegetation_index": 0.35
    },
    {
        "location_id": "LOC-ML-02",
        "name": "Upper Shillong - Laitkor Peak",
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "latitude": 25.5450,
        "longitude": 91.8795,
        "elevation": 1780.0,
        "slope": 28.0,
        "aspect": "NE",
        "terrain_roughness": 16.0,
        "geology_type": "Shillong Group Quartzites & Phyllites",
        "vegetation_type": "Khasi Pine (Pinus kesiya) Forest",
        "rainfall_1h": 2.0,
        "rainfall_24h": 28.0,
        "rainfall_7d": 80.0,
        "soil_moisture": 45.0,
        "vegetation_index": 0.76
    },
    {
        "location_id": "LOC-MN-01",
        "name": "Tupul Railway Corridor (Ijei River Valley)",
        "state": "Manipur",
        "district": "Noney",
        "latitude": 24.8150,
        "longitude": 93.6350,
        "elevation": 740.0,
        "slope": 43.0,
        "aspect": "SW",
        "terrain_roughness": 38.0,
        "geology_type": "Tertiary Disang Shale, heavily weathered cut-slopes",
        "vegetation_type": "Degraded mixed secondary forest",
        "rainfall_1h": 18.5,
        "rainfall_24h": 118.0,
        "rainfall_7d": 310.0,
        "soil_moisture": 88.0,
        "vegetation_index": 0.42
    },
    {
        "location_id": "LOC-MN-02",
        "name": "Langol Hills - Lamphelpat Slopes",
        "state": "Manipur",
        "district": "Imphal West",
        "latitude": 24.8355,
        "longitude": 93.9120,
        "elevation": 820.0,
        "slope": 26.0,
        "aspect": "E",
        "terrain_roughness": 14.0,
        "geology_type": "Disang Series Sandstone & Siltstone",
        "vegetation_type": "Subtropical Pine-Oak Broadleaf",
        "rainfall_1h": 1.5,
        "rainfall_24h": 18.0,
        "rainfall_7d": 55.0,
        "soil_moisture": 38.0,
        "vegetation_index": 0.68
    },
    {
        "location_id": "LOC-MZ-01",
        "name": "Laipuitlang - Durtlang Hill Escarpment",
        "state": "Mizoram",
        "district": "Aizawl",
        "latitude": 23.7460,
        "longitude": 92.7176,
        "elevation": 1180.0,
        "slope": 46.0,
        "aspect": "W",
        "terrain_roughness": 40.0,
        "geology_type": "Surma Group Sandstone-Shale interbeds, steep dip slopes",
        "vegetation_type": "Urban slope fringe, mixed bamboo",
        "rainfall_1h": 15.0,
        "rainfall_24h": 92.0,
        "rainfall_7d": 240.0,
        "soil_moisture": 82.0,
        "vegetation_index": 0.51
    },
    {
        "location_id": "LOC-MZ-02",
        "name": "Zokhawthar Border Transit Corridor",
        "state": "Mizoram",
        "district": "Champhai",
        "latitude": 23.3644,
        "longitude": 93.3320,
        "elevation": 1320.0,
        "slope": 35.0,
        "aspect": "E",
        "terrain_roughness": 26.0,
        "geology_type": "Upper Bhuban Siltstone and Mudstone",
        "vegetation_type": "Montane wet temperate forest",
        "rainfall_1h": 3.0,
        "rainfall_24h": 32.0,
        "rainfall_7d": 90.0,
        "soil_moisture": 52.0,
        "vegetation_index": 0.70
    },
    {
        "location_id": "LOC-NL-01",
        "name": "NH-29 Bypass / Jotsoma Sinking Zone",
        "state": "Nagaland",
        "district": "Kohima",
        "latitude": 25.6700,
        "longitude": 94.0800,
        "elevation": 1490.0,
        "slope": 39.0,
        "aspect": "NW",
        "terrain_roughness": 32.0,
        "geology_type": "Disang flysch sediments, intensive active creep zone",
        "vegetation_type": "Secondary scrub and terraced agriculture",
        "rainfall_1h": 12.0,
        "rainfall_24h": 78.0,
        "rainfall_7d": 210.0,
        "soil_moisture": 77.0,
        "vegetation_index": 0.54
    },
    {
        "location_id": "LOC-NL-02",
        "name": "Ungma - Mokokchung Ridge",
        "state": "Nagaland",
        "district": "Mokokchung",
        "latitude": 26.3100,
        "longitude": 94.5200,
        "elevation": 1330.0,
        "slope": 31.0,
        "aspect": "NE",
        "terrain_roughness": 20.0,
        "geology_type": "Barail Sandstones with clay lenses",
        "vegetation_type": "Subtropical broadleaf forest",
        "rainfall_1h": 2.5,
        "rainfall_24h": 24.0,
        "rainfall_7d": 72.0,
        "soil_moisture": 48.0,
        "vegetation_index": 0.65
    },
    {
        "location_id": "LOC-SK-01",
        "name": "Pakyong - Burtuk Corridor",
        "state": "Sikkim",
        "district": "Gangtok",
        "latitude": 27.2400,
        "longitude": 88.5900,
        "elevation": 1680.0,
        "slope": 42.0,
        "aspect": "E",
        "terrain_roughness": 36.0,
        "geology_type": "Daling Group Chlorite-Sericite Schists & Phyllites",
        "vegetation_type": "Himalayan Wet Temperate Forest",
        "rainfall_1h": 16.0,
        "rainfall_24h": 105.0,
        "rainfall_7d": 290.0,
        "soil_moisture": 84.0,
        "vegetation_index": 0.58
    },
    {
        "location_id": "LOC-SK-02",
        "name": "Chungthang - Dzongu Teesta Canyon",
        "state": "Sikkim",
        "district": "Mangan",
        "latitude": 27.6040,
        "longitude": 88.6470,
        "elevation": 1560.0,
        "slope": 49.0,
        "aspect": "N",
        "terrain_roughness": 52.0,
        "geology_type": "Central Himalayan Gneissic Complex, steep moraine slopes",
        "vegetation_type": "Subalpine Birch-Fir & Rhododendron scrub",
        "rainfall_1h": 21.0,
        "rainfall_24h": 135.0,
        "rainfall_7d": 360.0,
        "soil_moisture": 89.0,
        "vegetation_index": 0.40
    },
    {
        "location_id": "LOC-AR-01",
        "name": "Ganga Lake (Gekar Sinying) Slope Reserve",
        "state": "Arunachal Pradesh",
        "district": "Papum Pare (Itanagar)",
        "latitude": 27.0850,
        "longitude": 93.6050,
        "elevation": 460.0,
        "slope": 34.0,
        "aspect": "SE",
        "terrain_roughness": 22.0,
        "geology_type": "Siwalik Group Soft Sandstone and conglomerate",
        "vegetation_type": "Tropical Semi-evergreen rainforest",
        "rainfall_1h": 5.0,
        "rainfall_24h": 46.0,
        "rainfall_7d": 125.0,
        "soil_moisture": 62.0,
        "vegetation_index": 0.81
    },
    {
        "location_id": "LOC-AR-02",
        "name": "Sela Pass - Jang High Altitude Sector",
        "state": "Arunachal Pradesh",
        "district": "Tawang",
        "latitude": 27.5050,
        "longitude": 92.1020,
        "elevation": 3120.0,
        "slope": 47.0,
        "aspect": "N",
        "terrain_roughness": 46.0,
        "geology_type": "Higher Himalayan Gneiss with permafrost thaw zones",
        "vegetation_type": "Alpine scrub and talus scree",
        "rainfall_1h": 8.0,
        "rainfall_24h": 65.0,
        "rainfall_7d": 175.0,
        "soil_moisture": 71.0,
        "vegetation_index": 0.32
    },
    {
        "location_id": "LOC-TR-01",
        "name": "Jampui Hills (Vanghmun Escarpment)",
        "state": "Tripura",
        "district": "North Tripura",
        "latitude": 23.9450,
        "longitude": 92.2700,
        "elevation": 640.0,
        "slope": 29.0,
        "aspect": "W",
        "terrain_roughness": 19.0,
        "geology_type": "Tipam Sandstone and Bokabil Shale",
        "vegetation_type": "Orange orchard and bamboo brakes",
        "rainfall_1h": 2.0,
        "rainfall_24h": 22.0,
        "rainfall_7d": 65.0,
        "soil_moisture": 42.0,
        "vegetation_index": 0.69
    },
    {
        "location_id": "LOC-TR-02",
        "name": "Pilak Valley Slope Corridor",
        "state": "Tripura",
        "district": "South Tripura",
        "latitude": 23.2300,
        "longitude": 91.5600,
        "elevation": 140.0,
        "slope": 18.0,
        "aspect": "SW",
        "terrain_roughness": 11.0,
        "geology_type": "Dupitila Formation Unconsolidated Sands & Clays",
        "vegetation_type": "Moist deciduous sal forest",
        "rainfall_1h": 1.0,
        "rainfall_24h": 12.0,
        "rainfall_7d": 40.0,
        "soil_moisture": 32.0,
        "vegetation_index": 0.72
    }
]

HISTORICAL_EVENTS = [
    {
        "event_id": "HIST-2022-TUPUL",
        "location_name": "Tupul Railway Yard",
        "state": "Manipur",
        "district": "Noney",
        "latitude": 24.8150,
        "longitude": 93.6350,
        "event_date": datetime(2022, 6, 30, 0, 30, tzinfo=timezone.utc),
        "severity": "CATASTROPHIC",
        "triggering_rainfall_24h": 142.5,
        "triggering_rainfall_7d": 386.0,
        "slope": 44.0,
        "elevation": 720.0,
        "estimated_volume_m3": 650000.0,
        "casualties": 61,
        "infrastructure_damage": "Entire 107 Territorial Army camp obliterated; Ijei river dammed creating flash flood threat",
        "geological_formation": "Weathered Disang shale cut by deep railway bench excavations",
        "data_source": "Geological Survey of India (GSI) Geotechnical Post-Disaster Audit",
        "notes": "Triggered by prolonged 10-day rainfall combined with unengineered slope excavation cuts."
    },
    {
        "event_id": "HIST-2022-DIMA-HASAO",
        "location_name": "New Haflong Railway Station & Jatinga",
        "state": "Assam",
        "district": "Dima Hasao",
        "latitude": 25.1783,
        "longitude": 93.0250,
        "event_date": datetime(2022, 5, 16, 8, 45, tzinfo=timezone.utc),
        "severity": "CATASTROPHIC",
        "triggering_rainfall_24h": 218.0,
        "triggering_rainfall_7d": 520.0,
        "slope": 40.0,
        "elevation": 680.0,
        "estimated_volume_m3": 480000.0,
        "casualties": 14,
        "infrastructure_damage": "Lumding-Badarpur railway section completely buried; trains derailed and stations flooded",
        "geological_formation": "Barail and Disang Shales, massive mud and debris flows",
        "data_source": "NDMA / Northeast Frontier Railway Incident Report",
        "notes": "Cut off Barak Valley for over 2 months."
    },
    {
        "event_id": "HIST-2024-AIZAWL-MELTHUM",
        "location_name": "Melthum Stone Quarry & Hlimen",
        "state": "Mizoram",
        "district": "Aizawl",
        "latitude": 23.7020,
        "longitude": 92.7210,
        "event_date": datetime(2024, 5, 28, 6, 0, tzinfo=timezone.utc),
        "severity": "CATASTROPHIC",
        "triggering_rainfall_24h": 194.0,
        "triggering_rainfall_7d": 280.0,
        "slope": 48.0,
        "elevation": 1050.0,
        "estimated_volume_m3": 210000.0,
        "casualties": 34,
        "infrastructure_damage": "Multiple residential clusters collapsed, major quarry face slope failure",
        "geological_formation": "Middle Bhuban siltstone-sandstone interbed with adverse dip angles",
        "data_source": "Mizoram State Disaster Management Authority (MSDMA)",
        "notes": "Triggered by extreme cyclone Remal torrential downpour on weakened quarry walls."
    },
    {
        "event_id": "HIST-2023-CHUNGTHANG",
        "location_name": "Chungthang Hydro Dam & Dzongu",
        "state": "Sikkim",
        "district": "Mangan",
        "latitude": 27.6040,
        "longitude": 88.6470,
        "event_date": datetime(2023, 10, 4, 1, 30, tzinfo=timezone.utc),
        "severity": "CATASTROPHIC",
        "triggering_rainfall_24h": 165.0,
        "triggering_rainfall_7d": 340.0,
        "slope": 51.0,
        "elevation": 1620.0,
        "estimated_volume_m3": 850000.0,
        "casualties": 42,
        "infrastructure_damage": "Teesta III Chungthang Dam washed away; NH-10 connectivity severed",
        "geological_formation": "South Lhonak GLOF flash flood surge coupled with toe-erosion debris avalanches",
        "data_source": "GSI Sikkim Unit / National Remote Sensing Centre (NRSC)",
        "notes": "Co-seismic and hydrometeorological compounded disaster."
    },
    {
        "event_id": "HIST-2020-SUBANSIRI",
        "location_name": "Lower Subansiri Dam Axis Hills",
        "state": "Arunachal Pradesh",
        "district": "Lower Subansiri",
        "latitude": 27.5500,
        "longitude": 94.2600,
        "event_date": datetime(2020, 7, 11, 14, 0, tzinfo=timezone.utc),
        "severity": "HIGH",
        "triggering_rainfall_24h": 112.0,
        "triggering_rainfall_7d": 310.0,
        "slope": 38.0,
        "elevation": 420.0,
        "estimated_volume_m3": 120000.0,
        "casualties": 0,
        "infrastructure_damage": "Guard wall collapse and tunnel inlet blockage",
        "geological_formation": "Soft Siwalik sandstones prone to slaking when submerged",
        "data_source": "Central Electricity Authority / GSI",
        "notes": "Preventive monitoring had evacuated workers in advance."
    },
    {
        "event_id": "HIST-2021-MAWSHUN",
        "location_name": "Mawkdok Dympep Valley Road",
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "latitude": 25.3500,
        "longitude": 91.7500,
        "event_date": datetime(2021, 6, 18, 10, 15, tzinfo=timezone.utc),
        "severity": "HIGH",
        "triggering_rainfall_24h": 260.0,
        "triggering_rainfall_7d": 620.0,
        "slope": 45.0,
        "elevation": 1400.0,
        "estimated_volume_m3": 180000.0,
        "casualties": 4,
        "infrastructure_damage": "Shillong-Cherrapunji road cut into gorge",
        "geological_formation": "Cretaceous Mahadek sandstone escarpment",
        "data_source": "Meghalaya PWD & SDMA",
        "notes": "Massive rockfall triggered during peak monsoon burst."
    },
    {
        "event_id": "HIST-2023-KOHIMA-NH29",
        "location_name": "Phesama / Jotsoma Bypass Sector",
        "state": "Nagaland",
        "district": "Kohima",
        "latitude": 25.6500,
        "longitude": 94.1000,
        "event_date": datetime(2023, 7, 24, 18, 20, tzinfo=timezone.utc),
        "severity": "HIGH",
        "triggering_rainfall_24h": 88.0,
        "triggering_rainfall_7d": 245.0,
        "slope": 36.0,
        "elevation": 1440.0,
        "estimated_volume_m3": 95000.0,
        "casualties": 2,
        "infrastructure_damage": "National Highway 29 lifelines blocked for 12 days",
        "geological_formation": "Highly sheared carbonaceous shales of Disang group",
        "data_source": "Nagaland State Disaster Management Authority (NSDMA)",
        "notes": "Chronic sliding zone exacerbated by heavy goods vehicle vibration."
    },
    {
        "event_id": "HIST-2022-PAKYONG",
        "location_name": "Pakyong Green Airport Hill Approach",
        "state": "Sikkim",
        "district": "Pakyong",
        "latitude": 27.2300,
        "longitude": 88.5800,
        "event_date": datetime(2022, 8, 12, 11, 0, tzinfo=timezone.utc),
        "severity": "HIGH",
        "triggering_rainfall_24h": 124.0,
        "triggering_rainfall_7d": 330.0,
        "slope": 37.0,
        "elevation": 1410.0,
        "estimated_volume_m3": 75000.0,
        "casualties": 1,
        "infrastructure_damage": "Airport perimeter slope wall cracking and highway subsidence",
        "geological_formation": "Daling phyllite with high clay alteration",
        "data_source": "Airports Authority of India / GSI",
        "notes": "Stabilized using soil nails and reinforced gabions."
    }
]

def seed_database(db: Session) -> None:
    """
    Populates database with realistic North Eastern baseline sites,
    historical GSI events, threshold configuration, and live predictions.
    """
    # 1. Seed Threshold Settings
    existing_settings = db.query(SystemSettings).filter(SystemSettings.key == "landslide_thresholds").first()
    if not existing_settings:
        settings_record = SystemSettings(
            key="landslide_thresholds",
            threshold_low=25.0,
            threshold_moderate=50.0,
            threshold_high=75.0,
            updated_by="SYSTEM_INIT",
            notes="Default calibrated GSI Himalayan Landslide Risk Thresholds"
        )
        db.add(settings_record)
        db.commit()

    thresholds = (25.0, 50.0, 75.0)

    # 2. Seed Locations & Initial Predictions
    for loc_data in NER_LOCATIONS:
        loc_id = loc_data["location_id"]
        existing = db.query(Location).filter(Location.location_id == loc_id).first()
        if not existing:
            # Run ML prediction on the baseline environmental profile
            pred_input = {
                "location_id": loc_id,
                "latitude": loc_data["latitude"],
                "longitude": loc_data["longitude"],
                "rainfall_1h": loc_data["rainfall_1h"],
                "rainfall_24h": loc_data["rainfall_24h"],
                "rainfall_7d": loc_data["rainfall_7d"],
                "soil_moisture": loc_data["soil_moisture"],
                "slope": loc_data["slope"],
                "elevation": loc_data["elevation"],
                "terrain_roughness": loc_data["terrain_roughness"],
                "vegetation_index": loc_data["vegetation_index"]
            }
            pred_res = predict_landslide_risk(pred_input, thresholds=thresholds)

            risk_score = pred_res["risk_score"]
            risk_level = pred_res["risk_level"]
            engineered = pred_res["engineered_features"]
            raw_factors = pred_res["risk_factors"]

            explanation = generate_geotechnical_explanation(risk_level, risk_score, engineered, raw_factors)
            recs = generate_recommendations(risk_level, engineered)

            alert_status = "NORMAL"
            if risk_level == "SEVERE":
                alert_status = "CRITICAL"
            elif risk_level == "HIGH":
                alert_status = "WARNING"

            loc = Location(
                location_id=loc_id,
                name=loc_data["name"],
                state=loc_data["state"],
                district=loc_data["district"],
                latitude=loc_data["latitude"],
                longitude=loc_data["longitude"],
                elevation=loc_data["elevation"],
                slope=loc_data["slope"],
                aspect=loc_data["aspect"],
                terrain_roughness=loc_data["terrain_roughness"],
                geology_type=loc_data["geology_type"],
                vegetation_type=loc_data["vegetation_type"],
                monitoring_status="ACTIVE",
                risk_level=risk_level,
                current_risk_score=risk_score,
                alert_status=alert_status,
                latest_measurements={
                    "rainfall_1h": loc_data["rainfall_1h"],
                    "rainfall_24h": loc_data["rainfall_24h"],
                    "rainfall_7d": loc_data["rainfall_7d"],
                    "soil_moisture": loc_data["soil_moisture"],
                    "vegetation_index": loc_data["vegetation_index"],
                    "source": "DEMO_SEEDED_DATA"
                },
                latest_prediction={
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                    "probability": pred_res["probability"],
                    "confidence": pred_res["confidence"],
                    "recommendation": recs["recommendation"],
                    "explanation": explanation
                }
            )
            db.add(loc)
            db.commit()
            db.refresh(loc)

            # Add baseline prediction history
            pred_record = Prediction(
                location_id=loc_id,
                timestamp=utc_now() - timedelta(minutes=15),
                risk_score=risk_score,
                risk_level=risk_level,
                probability=pred_res["probability"],
                confidence=pred_res["confidence"],
                risk_factors=raw_factors,
                recommendation=recs["recommendation"],
                explanation=explanation,
                input_features=pred_input,
                model_version="v1.0.0-rf-ensemble"
            )
            db.add(pred_record)

            # Generate alerts if High or Severe
            if risk_level in ["HIGH", "SEVERE"]:
                alert = Alert(
                    alert_id=f"ALT-INIT-{loc_id}",
                    location_id=loc_id,
                    severity=risk_level,
                    status="ACTIVE",
                    risk_score=risk_score,
                    title=f"{risk_level} Landslide Hazard Warning: {loc.name}",
                    message=(
                        f"Autonomous warning triggered for {loc.name}, {loc.district}, {loc.state}. "
                        f"Risk score: {risk_score:.1f}/100. Soil saturation and rainfall exceed safety thresholds."
                    ),
                    triggering_factors=raw_factors,
                    recommended_action=recs["recommendation"],
                    sop_actions=recs["sop_actions"],
                    created_at=utc_now() - timedelta(minutes=15)
                )
                db.add(alert)

            db.commit()

    # 3. Seed Historical Landslide Events
    for hist in HISTORICAL_EVENTS:
        existing = db.query(HistoricalLandslide).filter(HistoricalLandslide.event_id == hist["event_id"]).first()
        if not existing:
            h_rec = HistoricalLandslide(**hist)
            db.add(h_rec)

    db.commit()
    print("Database successfully seeded with North Eastern locations, historical events, and active models.")
