"""
Configurable Thresholds and Regulatory References for Multi-Hazard Early Warning.

Regulatory and Scientific Baselines in India:
1. Air Quality:
   - Central Pollution Control Board (CPCB) National Ambient Air Quality Standards (NAAQS), 2009.
   - 24-hour standard: PM2.5 = 60 µg/m³, PM10 = 100 µg/m³.
   - AQI Category Breaks: Good (0-50), Satisfactory (51-100), Moderate (101-200),
     Poor (201-300), Very Poor (301-400), Severe (401-500).

2. Extreme Heat & Heatwave:
   - India Meteorological Department (IMD) Criteria:
     Plains: Max temp >= 40°C; Hills: Max temp >= 30°C.
     Heatwave: Departure 4.5°C to 6.4°C above normal or temp >= 45°C.
     Severe Heatwave: Departure > 6.4°C or temp >= 47°C.
   - NOAA / IMD Heat Index (Apparent Temperature):
     > 41°C: Extreme Caution / Cramps; > 54°C: Danger of Heatstroke.

3. Flood & Flash-Flood:
   - Central Water Commission (CWC) & IMD Guidelines:
     Heavy rainfall >= 64.5 mm/day; Very heavy >= 115.5 mm/day.
     Flash flood alert: Short-duration rainfall rate >= 20 mm/hr with
     rapid river water level rise rate >= 0.5 m/hr.

4. Forest Fire:
   - Forest Survey of India (FSI) & Canadian Forest Fire Weather Index (FWI) principles:
     High ambient temperature (> 38°C), low relative humidity (< 25%), and elevated
     combustion byproducts / smoke (> 40 ppm). Note: Requires satellite or ground confirmation.

5. Landslide Precursors:
   - Geological Survey of India (GSI) & NDMA Guidelines:
     Volumetric soil moisture saturation >= 75-80% combined with slope ground micro-vibrations
     (>= 0.05g) and cumulative rainfall. Warning: Precursor indicators only.

6. Industrial Gas Leakage:
   - CPCB / OSHA Industrial Ambient Exposure Limits:
     Baseline ambient volatile gas < 25 ppm; Warning >= 50 ppm; Hazardous >= 100 ppm; Critical >= 200 ppm.

7. Water Quality:
   - Bureau of Indian Standards (BIS IS 10500:2012) & CPCB Surface Water Criteria:
     pH: 6.5 - 8.5; Turbidity: <= 5 NTU (permissible up to 10 NTU); Dissolved Oxygen: >= 5.0 mg/L.
"""

from typing import Dict, Any
from pydantic import BaseModel, Field


class FloodThresholds(BaseModel):
    water_level_warning_m: float = Field(default=8.0, description="Warning stage water level in meters")
    water_level_danger_m: float = Field(default=10.0, description="Danger stage water level in meters")
    rise_rate_warning_m_h: float = Field(default=0.4, description="Water level rise rate warning threshold (m/hr)")
    rise_rate_critical_m_h: float = Field(default=0.8, description="Flash flood rapid rise rate threshold (m/hr)")
    heavy_rainfall_mm: float = Field(default=25.0, description="Short-duration rainfall warning threshold (mm)")
    torrential_rainfall_mm: float = Field(default=64.5, description="IMD Heavy rainfall threshold (mm/day)")


class ForestFireThresholds(BaseModel):
    temp_warning_c: float = Field(default=38.0, description="Elevated temperature threshold (°C)")
    temp_critical_c: float = Field(default=43.0, description="Extreme dry fire weather temperature (°C)")
    humidity_low_pct: float = Field(default=25.0, description="Low relative humidity threshold (%)")
    humidity_critical_pct: float = Field(default=15.0, description="Critically dry relative humidity (%)")
    smoke_warning_ppm: float = Field(default=40.0, description="Smoke/combustion byproduct warning (ppm)")
    smoke_critical_ppm: float = Field(default=80.0, description="Smoke/combustion byproduct critical (ppm)")


class AirPollutionThresholds(BaseModel):
    pm25_moderate_ug_m3: float = Field(default=60.0, description="CPCB 24-hr standard for PM2.5")
    pm25_poor_ug_m3: float = Field(default=90.0, description="Poor air quality PM2.5 threshold")
    pm25_severe_ug_m3: float = Field(default=150.0, description="Severe air quality PM2.5 threshold")
    pm10_moderate_ug_m3: float = Field(default=100.0, description="CPCB 24-hr standard for PM10")
    pm10_poor_ug_m3: float = Field(default=250.0, description="Poor air quality PM10 threshold")
    pm10_severe_ug_m3: float = Field(default=350.0, description="Severe air quality PM10 threshold")
    aqi_warning: float = Field(default=200.0, description="AQI Poor threshold")
    aqi_severe: float = Field(default=300.0, description="AQI Very Poor / Severe threshold")
    rate_of_change_pm25_ug_m3: float = Field(default=35.0, description="Sudden spike in PM2.5 threshold")


class ExtremeHeatThresholds(BaseModel):
    temp_warning_c: float = Field(default=40.0, description="IMD Plains heatwave baseline threshold (°C)")
    temp_severe_c: float = Field(default=45.0, description="IMD Severe heatwave threshold (°C)")
    heat_index_caution_c: float = Field(default=41.0, description="NOAA/IMD Heat index caution threshold (°C)")
    heat_index_danger_c: float = Field(default=54.0, description="NOAA/IMD Heat index danger threshold (°C)")


class LandslideThresholds(BaseModel):
    soil_moisture_warning_pct: float = Field(default=75.0, description="High soil pore saturation warning (%)")
    soil_moisture_critical_pct: float = Field(default=85.0, description="Near-saturated critical soil moisture (%)")
    vibration_warning_g: float = Field(default=0.04, description="Slope micro-movement vibration warning (g)")
    vibration_critical_g: float = Field(default=0.08, description="Slope displacement vibration critical (g)")
    rainfall_trigger_mm: float = Field(default=30.0, description="Precipitation triggering soil liquefaction (mm)")


class IndustrialGasThresholds(BaseModel):
    baseline_gas_ppm: float = Field(default=25.0, description="Normal ambient baseline gas (ppm)")
    gas_warning_ppm: float = Field(default=50.0, description="Gas concentration warning threshold (ppm)")
    gas_danger_ppm: float = Field(default=100.0, description="Gas concentration danger threshold (ppm)")
    gas_critical_ppm: float = Field(default=200.0, description="Immediate evacuation critical gas (ppm)")
    rate_of_change_ppm: float = Field(default=30.0, description="Sudden gas spike threshold (ppm)")


class WaterQualityThresholds(BaseModel):
    ph_min: float = Field(default=6.5, description="BIS IS 10500 Minimum safe pH")
    ph_max: float = Field(default=8.5, description="BIS IS 10500 Maximum safe pH")
    turbidity_warning_ntu: float = Field(default=10.0, description="Turbidity warning threshold (NTU)")
    turbidity_critical_ntu: float = Field(default=40.0, description="Turbidity severe contamination (NTU)")
    dissolved_oxygen_warning_mg_l: float = Field(default=5.0, description="Minimum healthy aquatic DO (mg/L)")
    dissolved_oxygen_critical_mg_l: float = Field(default=3.0, description="Severe hypoxia critical DO (mg/L)")


class EdgeThresholdConfig(BaseModel):
    """Container for all modular hazard detection thresholds."""
    flood: FloodThresholds = Field(default_factory=FloodThresholds)
    forest_fire: ForestFireThresholds = Field(default_factory=ForestFireThresholds)
    air_pollution: AirPollutionThresholds = Field(default_factory=AirPollutionThresholds)
    extreme_heat: ExtremeHeatThresholds = Field(default_factory=ExtremeHeatThresholds)
    landslide: LandslideThresholds = Field(default_factory=LandslideThresholds)
    industrial_gas: IndustrialGasThresholds = Field(default_factory=IndustrialGasThresholds)
    water_quality: WaterQualityThresholds = Field(default_factory=WaterQualityThresholds)

    # General statistical anomaly detection parameters
    z_score_threshold: float = Field(default=2.5, description="Standard deviations for statistical anomaly")
    moving_window_size: int = Field(default=20, description="Number of recent readings for rolling statistics")
    stale_reading_max_seconds: float = Field(default=3600.0, description="Readings older than this are flagged stale")


DEFAULT_THRESHOLDS = EdgeThresholdConfig()
