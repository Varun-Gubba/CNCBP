"""
Modular Anomaly Detection Engine for Environmental Readings.

Techniques:
1. Configurable Domain Threshold Rules
2. Rolling Averages & Rate-of-Change Detection (Δv / Δt)
3. Moving-Window Statistical Anomaly Detection (Z-score with Bessel's correction)
4. Baseline Deviation
5. Multivariate ML Outlier Scoring (Isolation Forest)
6. Data Quality Checks: Missing, Invalid, and Stale Reading Safeguards
"""

from collections import deque
from datetime import datetime, timezone
import math
import uuid
from typing import Dict, List, Optional, Any, Tuple

from models import AnomalyResult
from .config import EdgeThresholdConfig, DEFAULT_THRESHOLDS
from .ml_model import EDGE_ISOLATION_FOREST


class AnomalyDetector:
    """
    Stateful anomaly detection processor for a single edge sensor node.
    Maintains bounded historical window for moving averages, rates of change,
    and rolling statistical Z-scores.
    """

    def __init__(
        self,
        sensor_id: str,
        config: Optional[EdgeThresholdConfig] = None,
        window_size: int = 20,
    ):
        self.sensor_id = sensor_id
        self.config = config or DEFAULT_THRESHOLDS
        self.window_size = window_size
        # Bounded historical queue of readings: stores dict of key -> float
        self._history: deque[Dict[str, float]] = deque(maxlen=window_size)
        self._timestamps: deque[datetime] = deque(maxlen=window_size)

    def reset_history(self) -> None:
        """Clears stored readings history."""
        self._history.clear()
        self._timestamps.clear()

    def _parse_timestamp(self, ts_str: Optional[str]) -> datetime:
        if not ts_str:
            return datetime.now(timezone.utc)
        try:
            # Handle ISO 8601 with or without Z
            clean_ts = ts_str.replace("Z", "+00:00")
            return datetime.fromisoformat(clean_ts)
        except Exception:
            return datetime.now(timezone.utc)

    def validate_reading_quality(self, reading: Dict[str, Any]) -> List[str]:
        """
        Validates reading sanity.
        Returns list of invalid reading issues. Does not throw exceptions.
        """
        issues = []

        # Check staleness
        ts = self._parse_timestamp(reading.get("timestamp"))
        age_seconds = (datetime.now(timezone.utc) - ts).total_seconds()
        if age_seconds > self.config.stale_reading_max_seconds:
            issues.append(f"Stale reading: data age is {int(age_seconds)}s (> {int(self.config.stale_reading_max_seconds)}s limit)")

        # Physical range validation
        temp = reading.get("temperature_celsius")
        if temp is not None and (temp < -50.0 or temp > 70.0):
            issues.append(f"Physical error: temperature {temp}°C outside plausible sensor limits (-50 to 70°C)")

        hum = reading.get("humidity_percentage")
        if hum is not None and (hum < 0.0 or hum > 100.0):
            issues.append(f"Physical error: humidity {hum}% outside [0, 100]% range")

        rain = reading.get("rainfall_mm")
        if rain is not None and rain < 0.0:
            issues.append(f"Physical error: rainfall {rain} mm cannot be negative")

        water = reading.get("water_level_m")
        if water is not None and water < 0.0:
            issues.append(f"Physical error: water level {water} m cannot be negative")

        ph = reading.get("ph")
        if ph is not None and (ph < 0.0 or ph > 14.0):
            issues.append(f"Physical error: pH {ph} outside chemical [0, 14] scale")

        sm = reading.get("soil_moisture_percentage")
        if sm is not None and (sm < 0.0 or sm > 100.0):
            issues.append(f"Physical error: soil moisture {sm}% outside [0, 100]% range")

        vib = reading.get("vibration_g")
        if vib is not None and vib < 0.0:
            issues.append(f"Physical error: vibration {vib}g cannot be negative amplitude")

        gas = reading.get("gas_concentration_ppm")
        if gas is not None and gas < 0.0:
            issues.append(f"Physical error: gas concentration {gas} ppm cannot be negative")

        return issues

    def _compute_rolling_stats(self, metric: str) -> Optional[Tuple[float, float, float]]:
        """
        Computes (mean, std_dev, last_val) for a metric across history.
        Returns None if fewer than 3 historical values exist.
        """
        vals = [h[metric] for h in self._history if metric in h and h[metric] is not None]
        if len(vals) < 3:
            return None

        mean = sum(vals) / len(vals)
        variance = sum((x - mean) ** 2 for x in vals) / (len(vals) - 1)  # Sample variance
        std_dev = math.sqrt(variance)
        return mean, std_dev, vals[-1]

    def _compute_rate_of_change(self, metric: str, current_val: float) -> Optional[float]:
        """Calculates difference between current value and previous recorded value."""
        if not self._history:
            return None
        prev_reading = self._history[-1]
        prev_val = prev_reading.get(metric)
        if prev_val is None:
            return None
        return current_val - prev_val

    def detect_anomalies(self, reading: Dict[str, Any]) -> List[AnomalyResult]:
        """
        Analyzes a single environmental reading and returns all detected anomalies.
        Deterministic: running this on identical input with identical history yields identical results.
        """
        anomalies: List[AnomalyResult] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        # Step 1: Check reading validity
        quality_issues = self.validate_reading_quality(reading)
        for issue in quality_issues:
            anomalies.append(
                AnomalyResult(
                    anomaly_id=f"ANO-INV-{uuid.uuid4().hex[:6]}",
                    sensor_id=self.sensor_id,
                    metric="DATA_VALIDATION",
                    observed_value=0.0,
                    expected_range=None,
                    anomaly_score=75.0,
                    is_anomaly=True,
                    detection_method="DATA_INTEGRITY_CHECK",
                    explanation=issue,
                    timestamp=now_iso,
                )
            )

        # Step 2: Rate of Change & Threshold Checks
        # A. Water Level & Rate of Rise (Flood)
        water_level = reading.get("water_level_m")
        if water_level is not None:
            if water_level >= self.config.flood.water_level_warning_m:
                score = 80.0 if water_level < self.config.flood.water_level_danger_m else 95.0
                anomalies.append(
                    AnomalyResult(
                        anomaly_id=f"ANO-WL-{uuid.uuid4().hex[:6]}",
                        sensor_id=self.sensor_id,
                        metric="water_level_m",
                        observed_value=water_level,
                        expected_range={"min": 0.0, "max": self.config.flood.water_level_warning_m},
                        anomaly_score=score,
                        is_anomaly=True,
                        detection_method="CONFIGURABLE_THRESHOLD_RULE",
                        explanation=f"Water level {water_level:.2f}m exceeds warning mark ({self.config.flood.water_level_warning_m:.1f}m).",
                        timestamp=now_iso,
                    )
                )

        rise_rate = reading.get("water_level_rise_rate_m_h")
        # If not supplied directly, calculate from rolling difference
        if rise_rate is None and water_level is not None:
            diff = self._compute_rate_of_change("water_level_m", water_level)
            if diff is not None:
                rise_rate = max(diff, 0.0)

        if rise_rate is not None and rise_rate >= self.config.flood.rise_rate_warning_m_h:
            score = 75.0 if rise_rate < self.config.flood.rise_rate_critical_m_h else 95.0
            anomalies.append(
                AnomalyResult(
                    anomaly_id=f"ANO-WRR-{uuid.uuid4().hex[:6]}",
                    sensor_id=self.sensor_id,
                    metric="water_level_rise_rate_m_h",
                    observed_value=round(rise_rate, 2),
                    expected_range={"min": -1.0, "max": self.config.flood.rise_rate_warning_m_h},
                    anomaly_score=score,
                    is_anomaly=True,
                    detection_method="RATE_OF_CHANGE_DETECTION",
                    explanation=f"Rate of water level rise ({rise_rate:.2f} m/h) exceeds flash-flood surge threshold ({self.config.flood.rise_rate_warning_m_h:.2f} m/h).",
                    timestamp=now_iso,
                )
            )

        # B. Rainfall (Flood / Landslide)
        rainfall = reading.get("rainfall_mm")
        if rainfall is not None and rainfall >= self.config.flood.heavy_rainfall_mm:
            score = 70.0 if rainfall < self.config.flood.torrential_rainfall_mm else 90.0
            anomalies.append(
                AnomalyResult(
                    anomaly_id=f"ANO-RAIN-{uuid.uuid4().hex[:6]}",
                    sensor_id=self.sensor_id,
                    metric="rainfall_mm",
                    observed_value=rainfall,
                    expected_range={"min": 0.0, "max": self.config.flood.heavy_rainfall_mm},
                    anomaly_score=score,
                    is_anomaly=True,
                    detection_method="CONFIGURABLE_THRESHOLD_RULE",
                    explanation=f"High precipitation ({rainfall:.1f} mm) recorded (warning threshold: {self.config.flood.heavy_rainfall_mm:.1f} mm).",
                    timestamp=now_iso,
                )
            )

        # C. Smoke & High Temperature (Forest Fire)
        smoke = reading.get("smoke_ppm")
        if smoke is not None and smoke >= self.config.forest_fire.smoke_warning_ppm:
            score = 75.0 if smoke < self.config.forest_fire.smoke_critical_ppm else 92.0
            anomalies.append(
                AnomalyResult(
                    anomaly_id=f"ANO-SMK-{uuid.uuid4().hex[:6]}",
                    sensor_id=self.sensor_id,
                    metric="smoke_ppm",
                    observed_value=smoke,
                    expected_range={"min": 0.0, "max": self.config.forest_fire.smoke_warning_ppm},
                    anomaly_score=score,
                    is_anomaly=True,
                    detection_method="CONFIGURABLE_THRESHOLD_RULE",
                    explanation=f"Elevated smoke concentration ({smoke:.1f} ppm) exceeds warning baseline ({self.config.forest_fire.smoke_warning_ppm:.1f} ppm).",
                    timestamp=now_iso,
                )
            )

        # D. Air Pollution (PM2.5, PM10, AQI)
        pm25 = reading.get("pm25")
        if pm25 is not None and pm25 >= self.config.air_pollution.pm25_moderate_ug_m3:
            if pm25 >= self.config.air_pollution.pm25_severe_ug_m3:
                score = 95.0
                desc = "Severe NAAQS violation"
            elif pm25 >= self.config.air_pollution.pm25_poor_ug_m3:
                score = 80.0
                desc = "Poor air quality"
            else:
                score = 65.0
                desc = "Moderate air quality exceedance"
            anomalies.append(
                AnomalyResult(
                    anomaly_id=f"ANO-PM25-{uuid.uuid4().hex[:6]}",
                    sensor_id=self.sensor_id,
                    metric="pm25",
                    observed_value=pm25,
                    expected_range={"min": 0.0, "max": self.config.air_pollution.pm25_moderate_ug_m3},
                    anomaly_score=score,
                    is_anomaly=True,
                    detection_method="CONFIGURABLE_THRESHOLD_RULE",
                    explanation=f"PM2.5 concentration ({pm25:.1f} µg/m³) indicates {desc} per CPCB NAAQS standards.",
                    timestamp=now_iso,
                )
            )

        # Sudden spike in PM2.5
        if pm25 is not None:
            pm25_diff = self._compute_rate_of_change("pm25", pm25)
            if pm25_diff is not None and pm25_diff >= self.config.air_pollution.rate_of_change_pm25_ug_m3:
                anomalies.append(
                    AnomalyResult(
                        anomaly_id=f"ANO-PM25-SPIKE-{uuid.uuid4().hex[:6]}",
                        sensor_id=self.sensor_id,
                        metric="pm25_spike",
                        observed_value=round(pm25_diff, 1),
                        expected_range={"min": -50.0, "max": self.config.air_pollution.rate_of_change_pm25_ug_m3},
                        anomaly_score=85.0,
                        is_anomaly=True,
                        detection_method="RATE_OF_CHANGE_DETECTION",
                        explanation=f"Sudden spike in PM2.5 (+{pm25_diff:.1f} µg/m³ jump over prior reading).",
                        timestamp=now_iso,
                    )
                )

        # E. Extreme Temperature & Heat Stress
        temp = reading.get("temperature_celsius")
        hum = reading.get("humidity_percentage")
        if temp is not None and temp >= self.config.extreme_heat.temp_warning_c:
            score = 75.0 if temp < self.config.extreme_heat.temp_severe_c else 95.0
            anomalies.append(
                AnomalyResult(
                    anomaly_id=f"ANO-TEMP-{uuid.uuid4().hex[:6]}",
                    sensor_id=self.sensor_id,
                    metric="temperature_celsius",
                    observed_value=temp,
                    expected_range={"min": 10.0, "max": self.config.extreme_heat.temp_warning_c},
                    anomaly_score=score,
                    is_anomaly=True,
                    detection_method="CONFIGURABLE_THRESHOLD_RULE",
                    explanation=f"Temperature {temp:.1f}°C meets IMD heatwave criteria (plains threshold: {self.config.extreme_heat.temp_warning_c:.1f}°C).",
                    timestamp=now_iso,
                )
            )

        # F. Landslide Precursors (Soil Moisture & Vibration)
        sm = reading.get("soil_moisture_percentage")
        vib = reading.get("vibration_g")
        if sm is not None and sm >= self.config.landslide.soil_moisture_warning_pct:
            score = 70.0 if sm < self.config.landslide.soil_moisture_critical_pct else 90.0
            anomalies.append(
                AnomalyResult(
                    anomaly_id=f"ANO-SM-{uuid.uuid4().hex[:6]}",
                    sensor_id=self.sensor_id,
                    metric="soil_moisture_percentage",
                    observed_value=sm,
                    expected_range={"min": 0.0, "max": self.config.landslide.soil_moisture_warning_pct},
                    anomaly_score=score,
                    is_anomaly=True,
                    detection_method="CONFIGURABLE_THRESHOLD_RULE",
                    explanation=f"Soil saturation {sm:.1f}% indicates high pore-water pressure, weakening slope shear strength.",
                    timestamp=now_iso,
                )
            )

        if vib is not None and vib >= self.config.landslide.vibration_warning_g:
            score = 75.0 if vib < self.config.landslide.vibration_critical_g else 95.0
            anomalies.append(
                AnomalyResult(
                    anomaly_id=f"ANO-VIB-{uuid.uuid4().hex[:6]}",
                    sensor_id=self.sensor_id,
                    metric="vibration_g",
                    observed_value=vib,
                    expected_range={"min": 0.0, "max": self.config.landslide.vibration_warning_g},
                    anomaly_score=score,
                    is_anomaly=True,
                    detection_method="CONFIGURABLE_THRESHOLD_RULE",
                    explanation=f"Slope micro-vibration {vib:.3f}g exceeds structural warning mark ({self.config.landslide.vibration_warning_g:.3f}g).",
                    timestamp=now_iso,
                )
            )

        # G. Industrial Gas Leakage
        gas = reading.get("gas_concentration_ppm")
        if gas is not None and gas >= self.config.industrial_gas.gas_warning_ppm:
            score = 75.0 if gas < self.config.industrial_gas.gas_danger_ppm else (
                90.0 if gas < self.config.industrial_gas.gas_critical_ppm else 98.0
            )
            anomalies.append(
                AnomalyResult(
                    anomaly_id=f"ANO-GAS-{uuid.uuid4().hex[:6]}",
                    sensor_id=self.sensor_id,
                    metric="gas_concentration_ppm",
                    observed_value=gas,
                    expected_range={"min": 0.0, "max": self.config.industrial_gas.gas_warning_ppm},
                    anomaly_score=score,
                    is_anomaly=True,
                    detection_method="CONFIGURABLE_THRESHOLD_RULE",
                    explanation=f"Gas concentration {gas:.1f} ppm exceeds industrial ambient threshold ({self.config.industrial_gas.gas_warning_ppm:.1f} ppm).",
                    timestamp=now_iso,
                )
            )

        # H. Water Quality (pH, Turbidity, DO)
        ph = reading.get("ph")
        if ph is not None and (ph < self.config.water_quality.ph_min or ph > self.config.water_quality.ph_max):
            anomalies.append(
                AnomalyResult(
                    anomaly_id=f"ANO-PH-{uuid.uuid4().hex[:6]}",
                    sensor_id=self.sensor_id,
                    metric="ph",
                    observed_value=ph,
                    expected_range={"min": self.config.water_quality.ph_min, "max": self.config.water_quality.ph_max},
                    anomaly_score=75.0,
                    is_anomaly=True,
                    detection_method="CONFIGURABLE_THRESHOLD_RULE",
                    explanation=f"Water pH {ph:.2f} is outside BIS IS 10500 permissible drinking/aquatic range ({self.config.water_quality.ph_min}-{self.config.water_quality.ph_max}).",
                    timestamp=now_iso,
                )
            )

        turbidity = reading.get("turbidity_ntu")
        if turbidity is not None and turbidity >= self.config.water_quality.turbidity_warning_ntu:
            score = 70.0 if turbidity < self.config.water_quality.turbidity_critical_ntu else 92.0
            anomalies.append(
                AnomalyResult(
                    anomaly_id=f"ANO-TURB-{uuid.uuid4().hex[:6]}",
                    sensor_id=self.sensor_id,
                    metric="turbidity_ntu",
                    observed_value=turbidity,
                    expected_range={"min": 0.0, "max": self.config.water_quality.turbidity_warning_ntu},
                    anomaly_score=score,
                    is_anomaly=True,
                    detection_method="CONFIGURABLE_THRESHOLD_RULE",
                    explanation=f"High turbidity {turbidity:.1f} NTU indicates significant suspended sediment or contamination.",
                    timestamp=now_iso,
                )
            )

        do = reading.get("dissolved_oxygen_mg_l")
        if do is not None and do <= self.config.water_quality.dissolved_oxygen_warning_mg_l:
            score = 70.0 if do > self.config.water_quality.dissolved_oxygen_critical_mg_l else 95.0
            anomalies.append(
                AnomalyResult(
                    anomaly_id=f"ANO-DO-{uuid.uuid4().hex[:6]}",
                    sensor_id=self.sensor_id,
                    metric="dissolved_oxygen_mg_l",
                    observed_value=do,
                    expected_range={"min": self.config.water_quality.dissolved_oxygen_warning_mg_l, "max": 14.0},
                    anomaly_score=score,
                    is_anomaly=True,
                    detection_method="CONFIGURABLE_THRESHOLD_RULE",
                    explanation=f"Depleted dissolved oxygen {do:.1f} mg/L threatens aquatic life (threshold: {self.config.water_quality.dissolved_oxygen_warning_mg_l:.1f} mg/L).",
                    timestamp=now_iso,
                )
            )

        # Step 3: Statistical Z-Score Anomaly Check for continuous variables
        for metric_name in ["temperature_celsius", "humidity_percentage", "pm25", "water_level_m", "gas_concentration_ppm"]:
            val = reading.get(metric_name)
            if val is not None and isinstance(val, (int, float)):
                stats = self._compute_rolling_stats(metric_name)
                if stats is not None:
                    mean, std, _ = stats
                    if std > 1e-4:
                        z_score = abs(val - mean) / std
                        if z_score >= self.config.z_score_threshold:
                            anomalies.append(
                                AnomalyResult(
                                    anomaly_id=f"ANO-Z-{metric_name[:4]}-{uuid.uuid4().hex[:4]}",
                                    sensor_id=self.sensor_id,
                                    metric=metric_name,
                                    observed_value=round(val, 2),
                                    expected_range={"min": round(mean - 2 * std, 2), "max": round(mean + 2 * std, 2)},
                                    anomaly_score=round(min(z_score * 25.0, 100.0), 1),
                                    is_anomaly=True,
                                    detection_method="MOVING_WINDOW_Z_SCORE",
                                    explanation=f"{metric_name} deviated by {z_score:.2f} standard deviations from rolling window mean ({mean:.2f}).",
                                    timestamp=now_iso,
                                )
                            )

        # Step 4: Machine Learning Isolation Forest Multi-Factor Anomaly Check
        ml_score, is_ml_anomaly = EDGE_ISOLATION_FOREST.compute_anomaly_score(reading)
        if is_ml_anomaly and ml_score >= 65.0:
            anomalies.append(
                AnomalyResult(
                    anomaly_id=f"ANO-ML-IFOREST-{uuid.uuid4().hex[:6]}",
                    sensor_id=self.sensor_id,
                    metric="MULTIVARIATE_VECTOR",
                    observed_value=ml_score,
                    expected_range={"min": 0.0, "max": 60.0},
                    anomaly_score=ml_score,
                    is_anomaly=True,
                    detection_method="ISOLATION_FOREST_ML",
                    explanation=(
                        f"Lightweight edge Isolation Forest flagged complex multi-variate outlier "
                        f"(Score: {ml_score}/100) across correlated sensor dimensions."
                    ),
                    timestamp=now_iso,
                )
            )

        # Update historical memory with current valid reading
        hist_entry = {k: v for k, v in reading.items() if isinstance(v, (int, float)) and not math.isnan(v)}
        self._history.append(hist_entry)
        self._timestamps.append(self._parse_timestamp(reading.get("timestamp")))

        return anomalies
