"""
Multi-Hazard Risk Engine and Severity Scoring.

Produces structured risk assessments across all seven environmental hazards:
1. Flood & Flash Flood
2. Forest Fire
3. Air Pollution
4. Extreme Heat
5. Landslide Precursors
6. Industrial Gas Leakage
7. Water Quality Degradation

All risk scores and confidence estimates use documented physical formulas.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

from models import (
    HazardType,
    SeverityLevel,
    RiskAssessment,
    AnomalyResult,
)
from .config import EdgeThresholdConfig, DEFAULT_THRESHOLDS


class RiskEngine:
    """
    Evaluates multi-hazard risk scores and generates structured RiskAssessment objects.
    Runs locally at the edge.
    """

    def __init__(self, config: Optional[EdgeThresholdConfig] = None):
        self.config = config or DEFAULT_THRESHOLDS

    def _determine_severity(self, risk_score: float) -> SeverityLevel:
        if risk_score >= 85.0:
            return SeverityLevel.CRITICAL
        elif risk_score >= 65.0:
            return SeverityLevel.HIGH
        elif risk_score >= 40.0:
            return SeverityLevel.MODERATE
        return SeverityLevel.LOW

    def _compute_confidence(
        self,
        present_keys: List[str],
        required_keys: List[str],
        history_len: int,
        corroborated: bool,
        is_stale: bool = False,
    ) -> float:
        """
        Defensible confidence score estimation:
        - Sensor completeness: up to 40 points
        - Historical window depth: up to 30 points
        - Cross-sensor corroboration: up to 30 points
        - Staleness penalty: -20 points
        """
        # 1. Completeness
        completeness_ratio = len(present_keys) / max(len(required_keys), 1)
        score = completeness_ratio * 40.0

        # 2. Window depth
        if history_len >= 10:
            score += 30.0
        elif history_len >= 5:
            score += 20.0
        elif history_len >= 2:
            score += 10.0
        else:
            score += 5.0

        # 3. Corroboration
        if corroborated:
            score += 30.0
        else:
            score += 10.0

        # 4. Penalty
        if is_stale:
            score -= 20.0

        return round(min(max(score, 15.0), 98.0), 1)

    def evaluate_all_hazards(
        self,
        sensor_id: str,
        location: str,
        reading: Dict[str, Any],
        anomalies: List[AnomalyResult],
        history_len: int = 5,
        is_stale: bool = False,
    ) -> Dict[str, RiskAssessment]:
        """Evaluates all hazards based on available telemetry."""
        assessments: Dict[str, RiskAssessment] = {}

        # 1. Flood Assessment
        assessments[HazardType.FLOOD.value] = self._assess_flood(
            sensor_id, location, reading, anomalies, history_len, is_stale
        )

        # 2. Forest Fire Assessment
        assessments[HazardType.FOREST_FIRE.value] = self._assess_forest_fire(
            sensor_id, location, reading, anomalies, history_len, is_stale
        )

        # 3. Air Pollution Assessment
        assessments[HazardType.AIR_POLLUTION.value] = self._assess_air_pollution(
            sensor_id, location, reading, anomalies, history_len, is_stale
        )

        # 4. Extreme Heat Assessment
        assessments[HazardType.EXTREME_HEAT.value] = self._assess_extreme_heat(
            sensor_id, location, reading, anomalies, history_len, is_stale
        )

        # 5. Landslide Precursor Assessment
        assessments[HazardType.LANDSLIDE_PRECURSOR.value] = self._assess_landslide(
            sensor_id, location, reading, anomalies, history_len, is_stale
        )

        # 6. Industrial Gas Assessment
        assessments[HazardType.INDUSTRIAL_GAS.value] = self._assess_industrial_gas(
            sensor_id, location, reading, anomalies, history_len, is_stale
        )

        # 7. Water Quality Assessment (Only if water quality sensors present)
        wq = self._assess_water_quality(sensor_id, location, reading, anomalies, history_len, is_stale)
        if wq is not None:
            assessments[HazardType.WATER_QUALITY.value] = wq

        return assessments

    # --- A. Flood and Flash Flood ---
    def _assess_flood(
        self,
        sensor_id: str,
        location: str,
        reading: Dict[str, Any],
        anomalies: List[AnomalyResult],
        history_len: int,
        is_stale: bool,
    ) -> RiskAssessment:
        now_iso = datetime.now(timezone.utc).isoformat()
        wl = reading.get("water_level_m")
        wrr = reading.get("water_level_rise_rate_m_h")
        rain = reading.get("rainfall_mm")

        present = [k for k in ["water_level_m", "water_level_rise_rate_m_h", "rainfall_mm"] if reading.get(k) is not None]
        contributing = {k: reading.get(k) for k in present}
        detected = [a.explanation for a in anomalies if a.metric in ("water_level_m", "water_level_rise_rate_m_h", "rainfall_mm")]

        if not present:
            return RiskAssessment(
                hazard_type=HazardType.FLOOD,
                sensor_id=sensor_id,
                location=location,
                risk_score=0.0,
                severity=SeverityLevel.LOW,
                confidence_score=20.0,
                detected_anomalies=[],
                contributing_measurements={},
                explanation="No hydrological or precipitation sensors available at this node.",
                recommended_action="Maintain routine monitoring; install level sensors if in riparian zone.",
                timestamp=now_iso,
                detection_method="BASELINE_HYDRO_RULES",
            )

        # Base risk calculation
        risk = 10.0
        corroborated = False

        if wl is not None:
            if wl >= self.config.flood.water_level_danger_m:
                risk += 50.0
            elif wl >= self.config.flood.water_level_warning_m:
                risk += 30.0

        if wrr is not None:
            if wrr >= self.config.flood.rise_rate_critical_m_h:
                risk += 40.0
            elif wrr >= self.config.flood.rise_rate_warning_m_h:
                risk += 25.0

        if rain is not None:
            if rain >= self.config.flood.torrential_rainfall_mm:
                risk += 30.0
            elif rain >= self.config.flood.heavy_rainfall_mm:
                risk += 18.0

        # Flash flood synergy: High rain + Rapid Rise
        if (rain is not None and rain >= self.config.flood.heavy_rainfall_mm) and \
           (wrr is not None and wrr >= self.config.flood.rise_rate_warning_m_h):
            risk += 20.0
            corroborated = True
            detected.append("Flash-flood trigger: Combined intense rainfall and rapidly rising water stage.")

        risk_score = round(min(risk, 98.0), 1)
        severity = self._determine_severity(risk_score)
        confidence = self._compute_confidence(present, ["water_level_m", "water_level_rise_rate_m_h", "rainfall_mm"], history_len, corroborated, is_stale)

        if severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH):
            action = "Dispatch immediate flash-flood evacuation alert to downstream settlements; open drainage weirs."
            explanation = "Critical flood surge detected from rising river stage and heavy precipitation."
        elif severity == SeverityLevel.MODERATE:
            action = "Alert regional flood control room; monitor weir telemetry closely."
            explanation = "Moderate hydrological elevation detected near warning baseline."
        else:
            action = "Hydrological conditions within normal flow bounds."
            explanation = "River stage and precipitation are normal."

        return RiskAssessment(
            hazard_type=HazardType.FLOOD,
            sensor_id=sensor_id,
            location=location,
            risk_score=risk_score,
            severity=severity,
            confidence_score=confidence,
            detected_anomalies=detected,
            contributing_measurements=contributing,
            explanation=explanation,
            recommended_action=action,
            timestamp=now_iso,
            detection_method="HYDROLOGICAL_RATE_AND_STAGE_RULES",
        )

    # --- B. Forest Fire ---
    def _assess_forest_fire(
        self,
        sensor_id: str,
        location: str,
        reading: Dict[str, Any],
        anomalies: List[AnomalyResult],
        history_len: int,
        is_stale: bool,
    ) -> RiskAssessment:
        now_iso = datetime.now(timezone.utc).isoformat()
        temp = reading.get("temperature_celsius")
        hum = reading.get("humidity_percentage")
        smoke = reading.get("smoke_ppm")

        present = [k for k in ["temperature_celsius", "humidity_percentage", "smoke_ppm"] if reading.get(k) is not None]
        contributing = {k: reading.get(k) for k in present}
        detected = [a.explanation for a in anomalies if a.metric in ("smoke_ppm",)]

        risk = 10.0
        corroborated = False

        if smoke is not None:
            if smoke >= self.config.forest_fire.smoke_critical_ppm:
                risk += 45.0
            elif smoke >= self.config.forest_fire.smoke_warning_ppm:
                risk += 25.0

        if temp is not None:
            if temp >= self.config.forest_fire.temp_critical_c:
                risk += 25.0
            elif temp >= self.config.forest_fire.temp_warning_c:
                risk += 15.0

        if hum is not None:
            if hum <= self.config.forest_fire.humidity_critical_pct:
                risk += 25.0
            elif hum <= self.config.forest_fire.humidity_low_pct:
                risk += 15.0

        # Synergy: High temp + Low humidity + Smoke
        if (temp and temp >= self.config.forest_fire.temp_warning_c) and \
           (hum and hum <= self.config.forest_fire.humidity_low_pct) and \
           (smoke and smoke >= self.config.forest_fire.smoke_warning_ppm):
            risk += 20.0
            corroborated = True
            detected.append("Fire triangle alert: Combined extreme dry heat, desiccated vegetation humidity, and smoke.")

        risk_score = round(min(risk, 96.0), 1)
        severity = self._determine_severity(risk_score)
        confidence = self._compute_confidence(present, ["temperature_celsius", "humidity_percentage", "smoke_ppm"], history_len, corroborated, is_stale)

        explanation = (
            "Multi-sensor fire weather indicator. NOTE: These sensor readings alone do not prove an active "
            "forest blaze exists; satellite thermal anomaly detection or forest ranger patrols are required."
        )

        if severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH):
            action = "Alert divisional forest officer (DFO); verify via satellite MODIS/VIIRS thermal feed."
        elif severity == SeverityLevel.MODERATE:
            action = "Elevate fire danger watch; restrict burning activities in reserve forest zone."
        else:
            action = "Ambient conditions nominal; regular fire watch."

        return RiskAssessment(
            hazard_type=HazardType.FOREST_FIRE,
            sensor_id=sensor_id,
            location=location,
            risk_score=risk_score,
            severity=severity,
            confidence_score=confidence,
            detected_anomalies=detected,
            contributing_measurements=contributing,
            explanation=explanation,
            recommended_action=action,
            timestamp=now_iso,
            detection_method="THERMAL_HYGROMETRIC_SMOKE_FUSION",
        )

    # --- C. Air Pollution ---
    def _assess_air_pollution(
        self,
        sensor_id: str,
        location: str,
        reading: Dict[str, Any],
        anomalies: List[AnomalyResult],
        history_len: int,
        is_stale: bool,
    ) -> RiskAssessment:
        now_iso = datetime.now(timezone.utc).isoformat()
        pm25 = reading.get("pm25")
        pm10 = reading.get("pm10")
        aqi = reading.get("air_quality_aqi")

        present = [k for k in ["pm25", "pm10", "air_quality_aqi"] if reading.get(k) is not None]
        contributing = {k: reading.get(k) for k in present}
        detected = [a.explanation for a in anomalies if "pm25" in a.metric or "aqi" in a.metric]

        risk = 15.0
        corroborated = False

        if pm25 is not None:
            if pm25 >= self.config.air_pollution.pm25_severe_ug_m3:
                risk += 60.0
            elif pm25 >= self.config.air_pollution.pm25_poor_ug_m3:
                risk += 40.0
            elif pm25 >= self.config.air_pollution.pm25_moderate_ug_m3:
                risk += 20.0

        if aqi is not None:
            if aqi >= self.config.air_pollution.aqi_severe:
                risk += 50.0
            elif aqi >= self.config.air_pollution.aqi_warning:
                risk += 30.0

        if (pm25 and pm25 >= self.config.air_pollution.pm25_poor_ug_m3) and (aqi and aqi >= self.config.air_pollution.aqi_warning):
            corroborated = True

        risk_score = round(min(risk, 98.0), 1)
        severity = self._determine_severity(risk_score)
        confidence = self._compute_confidence(present, ["pm25", "air_quality_aqi"], history_len, corroborated, is_stale)

        explanation = (
            f"Air quality assessed against CPCB NAAQS (24-hr PM2.5 limit: "
            f"{self.config.air_pollution.pm25_moderate_ug_m3} µg/m³)."
        )

        if severity == SeverityLevel.CRITICAL:
            action = "Issue public smog advisory; halt construction and diesel generator sets (GRAP Stage IV)."
        elif severity == SeverityLevel.HIGH:
            action = "Advise sensitive groups and children to avoid outdoor exertion; deploy smog guns."
        elif severity == SeverityLevel.MODERATE:
            action = "Moderate air quality; monitor industrial corridors and vehicular emissions."
        else:
            action = "Air quality satisfactory; no emergency measures required."

        return RiskAssessment(
            hazard_type=HazardType.AIR_POLLUTION,
            sensor_id=sensor_id,
            location=location,
            risk_score=risk_score,
            severity=severity,
            confidence_score=confidence,
            detected_anomalies=detected,
            contributing_measurements=contributing,
            explanation=explanation,
            recommended_action=action,
            timestamp=now_iso,
            detection_method="CPCB_NAAQS_POLLUTION_INDEX",
        )

    # --- D. Extreme Heat ---
    def _assess_extreme_heat(
        self,
        sensor_id: str,
        location: str,
        reading: Dict[str, Any],
        anomalies: List[AnomalyResult],
        history_len: int,
        is_stale: bool,
    ) -> RiskAssessment:
        now_iso = datetime.now(timezone.utc).isoformat()
        temp = reading.get("temperature_celsius")
        hum = reading.get("humidity_percentage")

        present = [k for k in ["temperature_celsius", "humidity_percentage"] if reading.get(k) is not None]
        contributing = {k: reading.get(k) for k in present}
        detected = [a.explanation for a in anomalies if a.metric == "temperature_celsius"]

        risk = 10.0
        corroborated = False

        # Heat Index approximation
        heat_index = None
        if temp is not None and hum is not None:
            # Rothfusz Heat Index simplified regression
            heat_index = round(
                -8.78469475556 + 1.61139411 * temp + 2.33854883889 * hum
                - 0.14611605 * temp * hum - 0.012308094 * (temp ** 2)
                - 0.0164248277778 * (hum ** 2) + 0.002211732 * (temp ** 2) * hum
                + 0.00072546 * temp * (hum ** 2) - 0.000003582 * (temp ** 2) * (hum ** 2),
                1
            )
            contributing["estimated_heat_index_c"] = heat_index

        if temp is not None:
            if temp >= self.config.extreme_heat.temp_severe_c:
                risk += 65.0
            elif temp >= self.config.extreme_heat.temp_warning_c:
                risk += 45.0
            elif temp >= 36.0:
                risk += 20.0

        if heat_index is not None:
            if heat_index >= self.config.extreme_heat.heat_index_danger_c:
                risk += 30.0
                corroborated = True
            elif heat_index >= self.config.extreme_heat.heat_index_caution_c:
                risk += 15.0

        risk_score = round(min(risk, 98.0), 1)
        severity = self._determine_severity(risk_score)
        confidence = self._compute_confidence(present, ["temperature_celsius", "humidity_percentage"], history_len, corroborated, is_stale)

        explanation = (
            "Prototype heat-stress index based on dry-bulb temperature and apparent heat index. "
            "Distinguished from official IMD meteorological heatwave bulletins."
        )

        if severity == SeverityLevel.CRITICAL:
            action = "Issue extreme heatwave warning; open emergency cooling shelters and hydrate field workers."
        elif severity == SeverityLevel.HIGH:
            action = "Avoid direct midday sun exposure between 12 PM - 3 PM; ensure adequate public drinking water."
        elif severity == SeverityLevel.MODERATE:
            action = "Moderate thermal discomfort; advise hydration and ventilation."
        else:
            action = "Thermal conditions within comfortable range."

        return RiskAssessment(
            hazard_type=HazardType.EXTREME_HEAT,
            sensor_id=sensor_id,
            location=location,
            risk_score=risk_score,
            severity=severity,
            confidence_score=confidence,
            detected_anomalies=detected,
            contributing_measurements=contributing,
            explanation=explanation,
            recommended_action=action,
            timestamp=now_iso,
            detection_method="IMD_HEAT_INDEX_MODEL",
        )

    # --- E. Landslide Precursors ---
    def _assess_landslide(
        self,
        sensor_id: str,
        location: str,
        reading: Dict[str, Any],
        anomalies: List[AnomalyResult],
        history_len: int,
        is_stale: bool,
    ) -> RiskAssessment:
        now_iso = datetime.now(timezone.utc).isoformat()
        sm = reading.get("soil_moisture_percentage")
        vib = reading.get("vibration_g")
        rain = reading.get("rainfall_mm")

        present = [k for k in ["soil_moisture_percentage", "vibration_g", "rainfall_mm"] if reading.get(k) is not None]
        contributing = {k: reading.get(k) for k in present}
        detected = [a.explanation for a in anomalies if a.metric in ("soil_moisture_percentage", "vibration_g")]

        risk = 5.0
        corroborated = False

        if sm is not None:
            if sm >= self.config.landslide.soil_moisture_critical_pct:
                risk += 40.0
            elif sm >= self.config.landslide.soil_moisture_warning_pct:
                risk += 25.0

        if vib is not None:
            if vib >= self.config.landslide.vibration_critical_g:
                risk += 45.0
            elif vib >= self.config.landslide.vibration_warning_g:
                risk += 25.0

        if rain is not None:
            if rain >= self.config.landslide.rainfall_trigger_mm:
                risk += 20.0

        # Critical precursor synergy: High soil saturation + ground vibration
        if (sm and sm >= self.config.landslide.soil_moisture_warning_pct) and \
           (vib and vib >= self.config.landslide.vibration_warning_g):
            risk += 20.0
            corroborated = True
            detected.append("Precursor synergy: High pore-water saturation coupled with active geotechnical micro-vibrations.")

        risk_score = round(min(risk, 95.0), 1)
        severity = self._determine_severity(risk_score)
        confidence = self._compute_confidence(present, ["soil_moisture_percentage", "vibration_g"], history_len, corroborated, is_stale)

        explanation = (
            "Geotechnical precursor signs identified. Clearly communicated: These readings indicate "
            "potential slope stability warning signs, not a deterministic landslide prediction on their own."
        )

        if severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH):
            action = "Alert district disaster management authority (DDMA); inspect hillside road cuts and restrict slope traffic."
        elif severity == SeverityLevel.MODERATE:
            action = "Monitor slope tilt and pore pressure sensors; issue precautionary travel advisory."
        else:
            action = "Slope stability indicators nominal."

        return RiskAssessment(
            hazard_type=HazardType.LANDSLIDE_PRECURSOR,
            sensor_id=sensor_id,
            location=location,
            risk_score=risk_score,
            severity=severity,
            confidence_score=confidence,
            detected_anomalies=detected,
            contributing_measurements=contributing,
            explanation=explanation,
            recommended_action=action,
            timestamp=now_iso,
            detection_method="GEOTECHNICAL_PRECURSOR_RULES",
        )

    # --- F. Industrial Gas Leakage ---
    def _assess_industrial_gas(
        self,
        sensor_id: str,
        location: str,
        reading: Dict[str, Any],
        anomalies: List[AnomalyResult],
        history_len: int,
        is_stale: bool,
    ) -> RiskAssessment:
        now_iso = datetime.now(timezone.utc).isoformat()
        gas = reading.get("gas_concentration_ppm")
        temp = reading.get("temperature_celsius")

        present = [k for k in ["gas_concentration_ppm", "temperature_celsius"] if reading.get(k) is not None]
        contributing = {k: reading.get(k) for k in present}
        detected = [a.explanation for a in anomalies if a.metric == "gas_concentration_ppm"]

        risk = 5.0
        corroborated = False

        if gas is not None:
            if gas >= self.config.industrial_gas.gas_critical_ppm:
                risk = 98.0
            elif gas >= self.config.industrial_gas.gas_danger_ppm:
                risk = 85.0
            elif gas >= self.config.industrial_gas.gas_warning_ppm:
                risk = 60.0
            elif gas > self.config.industrial_gas.baseline_gas_ppm:
                risk = 35.0

        if gas and gas >= self.config.industrial_gas.gas_warning_ppm:
            corroborated = True

        risk_score = round(min(risk, 98.0), 1)
        severity = self._determine_severity(risk_score)
        confidence = self._compute_confidence(present, ["gas_concentration_ppm"], history_len, corroborated, is_stale)

        explanation = f"Industrial ambient gas evaluated against safety threshold ({self.config.industrial_gas.gas_warning_ppm} ppm baseline)."

        if severity == SeverityLevel.CRITICAL:
            action = "Initiate immediate plant perimeter evacuation; sound toxic gas alarm and alert HAZMAT teams."
        elif severity == SeverityLevel.HIGH:
            action = "Deploy leak detection and repair (LDAR) crew; verify ventilation scrubber operation."
        elif severity == SeverityLevel.MODERATE:
            action = "Elevated VOC / toxic gas level; inspect pipeline flanges and valves."
        else:
            action = "Gas levels within normal environmental limits."

        return RiskAssessment(
            hazard_type=HazardType.INDUSTRIAL_GAS,
            sensor_id=sensor_id,
            location=location,
            risk_score=risk_score,
            severity=severity,
            confidence_score=confidence,
            detected_anomalies=detected,
            contributing_measurements=contributing,
            explanation=explanation,
            recommended_action=action,
            timestamp=now_iso,
            detection_method="GAS_THRESHOLD_AND_SPIKE_DETECTION",
        )

    # --- G. Water Quality ---
    def _assess_water_quality(
        self,
        sensor_id: str,
        location: str,
        reading: Dict[str, Any],
        anomalies: List[AnomalyResult],
        history_len: int,
        is_stale: bool,
    ) -> Optional[RiskAssessment]:
        # Only evaluate if at least one water quality metric is provided
        present = [k for k in ["ph", "turbidity_ntu", "dissolved_oxygen_mg_l"] if reading.get(k) is not None]
        if not present:
            return None

        now_iso = datetime.now(timezone.utc).isoformat()
        ph = reading.get("ph")
        turb = reading.get("turbidity_ntu")
        do = reading.get("dissolved_oxygen_mg_l")

        contributing = {k: reading.get(k) for k in present}
        detected = [a.explanation for a in anomalies if a.metric in ("ph", "turbidity_ntu", "dissolved_oxygen_mg_l")]

        risk = 10.0
        corroborated = False

        if ph is not None:
            if ph < self.config.water_quality.ph_min or ph > self.config.water_quality.ph_max:
                risk += 35.0

        if turb is not None:
            if turb >= self.config.water_quality.turbidity_critical_ntu:
                risk += 45.0
            elif turb >= self.config.water_quality.turbidity_warning_ntu:
                risk += 25.0

        if do is not None:
            if do <= self.config.water_quality.dissolved_oxygen_critical_mg_l:
                risk += 45.0
            elif do <= self.config.water_quality.dissolved_oxygen_warning_mg_l:
                risk += 25.0

        if len(detected) >= 2:
            corroborated = True

        risk_score = round(min(risk, 98.0), 1)
        severity = self._determine_severity(risk_score)
        confidence = self._compute_confidence(present, ["ph", "turbidity_ntu", "dissolved_oxygen_mg_l"], history_len, corroborated, is_stale)

        explanation = "Water quality assessed against BIS IS 10500 standards (safe pH: 6.5-8.5, turbidity: <= 10 NTU, DO >= 5 mg/L)."

        if severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH):
            action = "Halt municipal drinking water intake; investigate upstream industrial effluent discharge."
        elif severity == SeverityLevel.MODERATE:
            action = "Increase coagulation dosing at treatment plant; retest grab samples."
        else:
            action = "Water parameters comply with potable and aquatic standards."

        return RiskAssessment(
            hazard_type=HazardType.WATER_QUALITY,
            sensor_id=sensor_id,
            location=location,
            risk_score=risk_score,
            severity=severity,
            confidence_score=confidence,
            detected_anomalies=detected,
            contributing_measurements=contributing,
            explanation=explanation,
            recommended_action=action,
            timestamp=now_iso,
            detection_method="BIS_IS_10500_WATER_CRITERIA",
        )
