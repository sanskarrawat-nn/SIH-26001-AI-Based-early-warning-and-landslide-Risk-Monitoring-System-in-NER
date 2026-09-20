from typing import Dict, Any, List

def generate_geotechnical_explanation(
    risk_level: str,
    risk_score: float,
    features: Dict[str, float],
    risk_factors: List[Dict[str, Any]]
) -> str:
    """
    Generates a domain-specific, physics-grounded explanation
    grounded strictly in the actual prediction features and factors.
    """
    slope = features.get("slope", 0.0)
    r24 = features.get("rainfall_24h", 0.0)
    r1 = features.get("rainfall_1h", 0.0)
    sm = features.get("soil_moisture", 0.0)
    ndvi = features.get("vegetation_index", 0.5)
    crit_ratio = features.get("critical_rainfall_ratio", 0.0)

    top_reasons = []

    if r24 >= 100.0:
        top_reasons.append(f"24-hour cumulative rainfall is severely elevated at {r24:.1f} mm (exceeding Himalayan antecedent saturation limits)")
    elif r24 >= 50.0:
        top_reasons.append(f"24-hour rainfall is moderate-to-heavy at {r24:.1f} mm")

    if r1 >= 25.0:
        top_reasons.append(f"a torrential cloudburst surge of {r1:.1f} mm/h is causing instantaneous overland runoff")

    if sm >= 80.0:
        top_reasons.append(f"soil moisture is at critical saturation ({sm:.1f}%), generating high pore-water pressure that diminishes internal shear strength")
    elif sm >= 60.0:
        top_reasons.append(f"soil moisture is elevated at {sm:.1f}%")

    if slope >= 38.0:
        top_reasons.append(f"the slope angle ({slope:.1f}°) significantly exceeds the angle of internal friction for weathered residual soil")
    elif slope >= 25.0:
        top_reasons.append(f"the terrain slope ({slope:.1f}°) imparts substantial gravitational shear stress")

    if ndvi < 0.30:
        top_reasons.append(f"sparse vegetative ground cover (NDVI: {ndvi:.2f}) provides minimal biotechnical root reinforcement")

    if not top_reasons:
        if risk_level == "LOW":
            return (
                f"Landslide hazard is currently assessed as LOW ({risk_score:.1f}/100). "
                f"Rainfall levels ({r24:.1f} mm/24h) remain well below the geological threshold, "
                f"soil moisture ({sm:.1f}%) is within safe baseline limits, and shear resistance exceeds gravitational driving stresses."
            )
        else:
            return (
                f"Landslide hazard is currently assessed as {risk_level} ({risk_score:.1f}/100). "
                f"Environmental measurements indicate standard seasonal variation across the hillside."
            )

    joined_reasons = " while ".join(top_reasons[:3])

    if risk_level == "SEVERE":
        return (
            f"CRITICAL INSTABILITY DETECTED: Risk is categorized as SEVERE ({risk_score:.1f}/100) primarily because {joined_reasons}. "
            f"The critical rainfall threshold ratio is at {int(crit_ratio * 100)}% of the slope failure limit, creating imminent danger of debris flow or rotational slip."
        )
    elif risk_level == "HIGH":
        return (
            f"ELEVATED HAZARD: Risk has escalated to HIGH ({risk_score:.1f}/100) primarily because {joined_reasons}. "
            f"Continued infiltration is expected to push effective normal stress to zero along the slip surface."
        )
    elif risk_level == "MODERATE":
        return (
            f"ELEVATED WATCH: Risk is classified as MODERATE ({risk_score:.1f}/100). Environmental indicators show that {joined_reasons}. "
            f"Close monitoring of ongoing precipitation is required."
        )
    else:
        return (
            f"STABLE: Risk is classified as LOW ({risk_score:.1f}/100). Even though {top_reasons[0]}, other stabilizing factors currently maintain slope integrity."
        )


def generate_recommendations(risk_level: str, features: Dict[str, float]) -> Dict[str, Any]:
    """
    Generates actionable early warning recommendations and Standard Operating Procedures (SOPs).
    """
    if risk_level == "SEVERE":
        action = "CRITICAL ALERT: Issue immediate evacuation orders for downstream settlements and vulnerable toe-slopes. Halt traffic on adjacent hill highway corridors."
        sop = [
            "Activate District Disaster Management Authority (DDMA) Incident Command Post",
            "Dispatch automated SMS/CAP alerts to village defense parties and vulnerable habitations",
            "Deploy Border Roads Organisation (BRO) / PWD heavy earthmovers to strategic standby points",
            "Impose immediate vehicular travel ban on identified high-risk highway bypasses",
            "Pre-position NDRF / SDRF search and rescue quick-reaction teams",
            "Establish 15-minute telemetry polling frequency on all rain-gauges and piezometers"
        ]
    elif risk_level == "HIGH":
        action = "WARNING: Issue preventive advisories. Restrict heavy vehicle movement along vulnerable hill cuttings and inspect roadside drainage culverts."
        sop = [
            "Notify DDMA nodal officers and local police outposts of potential slope failure",
            "Initiate emergency patrol along critical road sectors and river embankments",
            "Advise communities in low-lying gully beds to prepare for temporary shelter relocation",
            "Increase automated environmental sensor polling interval to 30 minutes",
            "Inspect and clear debris from retaining wall weepholes and lined drainage chutes"
        ]
    elif risk_level == "MODERATE":
        action = "ADVISORY: Increase monitoring cadence. Alert local emergency responders to track incoming weather radar and cumulative rainfall."
        sop = [
            "Maintain continuous telemetry monitoring on slope inclinometers and moisture probes",
            "Issue advisory to public works departments regarding potential loose boulder falls",
            "Review local emergency shelter availability and medical readiness"
        ]
    else:
        action = "NORMAL: Routine surveillance. Maintain standard environmental telemetry and structural inspection schedules."
        sop = [
            "Standard hourly monitoring of automated weather station telemetry",
            "Routine maintenance of catch-drains and vegetative slope bio-engineering"
        ]

    return {
        "recommendation": action,
        "sop_actions": sop
    }
