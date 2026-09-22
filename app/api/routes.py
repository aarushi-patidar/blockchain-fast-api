from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from app.services.battery_service import predict_battery_rul, get_health_status, get_recommendations
import math
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

router = APIRouter(
    prefix="/api",
    tags=["Battery Prediction"]
)


class SimpleBatteryInput(BaseModel):
    """Simplified battery parameters for RUL prediction"""
    current_capacity: float = Field(..., gt=0, description="Current capacity in Ahr (e.g., 2.0)")
    initial_capacity: float = Field(..., gt=0, description="Initial/Rated capacity in Ahr (e.g., 3.0)")
    ambient_temperature: float = Field(default=25.0, description="Ambient temperature in °C (e.g., 25)")
    cycle_count: int = Field(..., ge=0, description="Number of charge/discharge cycles (e.g., 50)")
    age_days: float = Field(..., ge=0, description="Battery age in days (e.g., 100)")


class BatteryPredictionResponse(BaseModel):
    """Response from battery prediction"""
    success: bool = Field(True, description="Whether prediction was successful")
    battery_metrics: Dict = Field(description="Battery input metrics")
    health_analysis: Dict = Field(description="Health status and metrics")
    rul_prediction: Dict = Field(description="RUL prediction results")
    recommendations: List[str] = Field(description="Recommendations based on battery state")


class BatteryHealthStatus(BaseModel):
    """Battery health status response"""
    soh_percentage: float = Field(description="State of Health as percentage (0-100)")
    health_status: str = Field(description="Health status category (EXCELLENT, GOOD, FAIR, POOR, CRITICAL)")
    health_description: str = Field(description="Description of health status")


class UserSurveyInput(BaseModel):
    """User survey input for battery capacity prediction via Gemini API"""
    listing_id: str = Field(..., description="Listing ID (UUID)")
    brand_model: str = Field(..., description="Battery brand and model (e.g., 'Samsung 18650')")
    initial_capacity: float = Field(..., gt=0, description="Initial capacity in Ahr (e.g., 3.0)")
    years_owned: int = Field(..., ge=0, description="Years the battery has been owned")
    primary_application: str = Field(..., description="Primary use: 'E-bike' or 'E-car'")
    avg_daily_usage: str = Field(..., description="Daily usage intensity: 'Light', 'Medium', or 'Heavy'")
    charging_frequency_in_week: int = Field(..., ge=0, description="Number of charge cycles per week")
    typical_charge_level: str = Field(..., description="Typical charge level: '20-80', '0-100', or 'Always Full'")
    avg_temperature: float = Field(default=25.0, description="Average operating temperature in °C")


class CapacityPredictionResponse(BaseModel):
    """Response from Gemini-based capacity prediction"""
    success: bool = Field(True, description="Whether prediction was successful")
    predicted_current_capacity: float = Field(description="Predicted current capacity in Ahr")
    confidence: float = Field(description="Confidence score of the prediction (0-100)")
    explanation: str = Field(description="Explanation of the prediction")
    input_summary: Dict = Field(description="Summary of input survey data")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Battery Prediction API is healthy ✅"
    }


@router.post("/predict-rul", response_model=BatteryPredictionResponse)
async def predict_rul(battery_data: SimpleBatteryInput):
    """
    Predict battery Remaining Useful Life (RUL) based on simplified battery metrics.
    
    This endpoint accepts basic battery parameters and returns comprehensive RUL predictions
    with health status and recommendations.
    
    Args:
        battery_data: Battery parameters (current capacity, initial capacity, temperature, cycles, age)
        
    Returns:
        BatteryPredictionResponse: Prediction results including RUL, health status, and recommendations
    """
    try:
        # Calculate State of Health (SoH)
        soh = battery_data.current_capacity / battery_data.initial_capacity
        soh_percentage = soh * 100
        
        # Calculate degradation factor
        degradation_factor = (1 - soh) * 100
        
        # Calculate degradation rate (percentage per cycle)
        if battery_data.cycle_count > 0:
            capacity_gradient_pct = (degradation_factor / battery_data.cycle_count)
        else:
            capacity_gradient_pct = 0.1
        
        # Build features dictionary for model prediction
        features_dict = {
            'Capacity': battery_data.current_capacity,
            'ambient_temperature': battery_data.ambient_temperature,
            'cycle_count': battery_data.cycle_count,
            'age_days': battery_data.age_days,
            'initial_capacity': battery_data.initial_capacity,
            'SoH': soh,
            'capacity_degradation': 1 - soh,
            'capacity_slope': -(battery_data.initial_capacity / (battery_data.cycle_count + 1)) if battery_data.cycle_count >= 0 else -0.01,
            'normalized_degradation_rate': -(1 - soh) / battery_data.initial_capacity if battery_data.initial_capacity > 0 else 0,
            'capacity_gradient_pct': capacity_gradient_pct,
            'cycle_utilization': battery_data.cycle_count / (battery_data.cycle_count + 100),
            'degradation_acceleration': ((1 - soh) ** 2) / max(battery_data.cycle_count, 1),
            'daily_degradation_rate': (1 - soh) / (battery_data.age_days + 1),
            'extrapolated_rul_from_gradient': (soh - 0.70) / (capacity_gradient_pct / 100) if capacity_gradient_pct > 0.0001 else 0,
            'cycle_duration': 3600.0,
            'measurement_count': 1000,
            'voltage_mean': 3.8,
            'voltage_std': 0.1,
            'voltage_min': 3.5,
            'voltage_max': 4.2,
            'voltage_range': 0.7,
            'voltage_drop': 0.5,
            'current_mean': -2.0,
            'current_std': 0.1,
            'current_min': -2.2,
            'current_max': -1.8,
            'temp_mean': battery_data.ambient_temperature,
            'temp_std': 2.0,
            'temp_min': battery_data.ambient_temperature - 2,
            'temp_max': battery_data.ambient_temperature + 2,
            'temp_range': 5.0,
            'power_mean': 7.6,
            'power_max': 9.2    
        }
        
        # Get prediction from model
        rul_prediction, _ = predict_battery_rul(features_dict)
        rul_cycles = max(0, int(rul_prediction))
        
        # Get health status
        status, description = get_health_status(soh)
        
        # Calculate estimated time to EOL (in days)
        if battery_data.cycle_count > 0 and battery_data.age_days > 0:
            avg_cycles_per_day = battery_data.cycle_count / battery_data.age_days
            if avg_cycles_per_day > 0:
                estimated_days = rul_cycles / avg_cycles_per_day
            else:
                estimated_days = rul_cycles * (battery_data.age_days / max(battery_data.cycle_count, 1))
        else:
            estimated_days = rul_cycles
        
        months = estimated_days / 30.44  # Average days per month
        
        # Get recommendations
        recommendations = get_recommendations(rul_prediction, soh, battery_data.cycle_count)
        
        return BatteryPredictionResponse(
            success=True,
            battery_metrics={
                "initial_capacity_ahr": round(battery_data.initial_capacity, 2),
                "current_capacity_ahr": round(battery_data.current_capacity, 2),
                "cycle_count": battery_data.cycle_count,
                "age_days": battery_data.age_days,
                "ambient_temperature_c": battery_data.ambient_temperature
            },
            health_analysis={
                "soh_percentage": round(soh_percentage, 1),
                "health_status": status,
                "health_description": description,
                "degradation_factor_percent": round(degradation_factor, 1)
            },
            rul_prediction={
                "rul_cycles": rul_cycles,
                "estimated_days_to_eol": round(estimated_days, 0),
                "estimated_time_to_eol": f"{int(estimated_days)} days (~{months:.1f} months)"
            },
            recommendations=recommendations
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Prediction error: {str(e)}")


@router.get("/health-status/{soh_percentage}")
async def get_battery_status(soh_percentage: float):
    """
    Get battery health status for a given State of Health percentage value.
    
    Args:
        soh_percentage: State of Health as percentage (0-100)
        
    Returns:
        BatteryHealthStatus: Health status details
    """
    if soh_percentage < 0 or soh_percentage > 100:
        raise HTTPException(status_code=400, detail="SoH percentage must be between 0 and 100")
    
    soh = soh_percentage / 100
    status, description = get_health_status(soh)
    
    return BatteryHealthStatus(
        soh_percentage=soh_percentage,
        health_status=status,
        health_description=description
    )


@router.get("/test-prediction")
async def test_prediction_endpoint():
    """
    Test endpoint with example battery data from the provided test case.
    
    Example values:
    - Current Capacity: 2 Ahr
    - Initial Capacity: 3 Ahr
    - Cycle Count: 40
    - Age: 300 days
    - Ambient Temperature: 29°C
    """
    example_data = SimpleBatteryInput(
        current_capacity=2.0,
        initial_capacity=3.0,
        ambient_temperature=29,
        cycle_count=40,
        age_days=300
    )
    
    return await predict_rul(example_data)


def calculate_battery_degradation(survey_data: UserSurveyInput) -> Dict:
    """
    Calculate battery degradation using heuristic-based algorithm.
    No external API required.
    
    Args:
        survey_data: User survey input
        
    Returns:
        Dict with 'predicted_capacity', 'confidence', 'explanation'
    """
    
    # Base degradation factors
    soh = 100.0  # Start at 100%
    
    # 1. Time-based degradation (calendric aging)
    # ~2-3% per year at room temperature
    years_degradation = survey_data.years_owned * 2.5
    soh -= years_degradation
    
    # 2. Usage intensity degradation
    usage_factor = {
        "Light": 0.5,      # 0.5% per year
        "Medium": 1.5,     # 1.5% per year
        "Heavy": 3.0       # 3.0% per year
    }.get(survey_data.avg_daily_usage, 1.5)
    
    usage_degradation = survey_data.years_owned * usage_factor
    soh -= usage_degradation
    
    # 3. Charging pattern impact
    charging_factor = {
        "20-80": 0.3,          # Conservative - minimal stress
        "0-100": 1.0,          # Moderate stress
        "Always Full": 1.8     # Maximum stress
    }.get(survey_data.typical_charge_level, 1.0)
    
    charging_degradation = survey_data.years_owned * charging_factor
    soh -= charging_degradation
    
    # 4. Temperature effects (exponential)
    # 25°C is optimal
    temp_delta = abs(survey_data.avg_temperature - 25.0)
    temp_factor = 1.0 + (temp_delta / 10.0) * 0.5  # 50% more degradation per 10°C
    temp_degradation = years_degradation * temp_factor * 0.3
    soh -= min(temp_degradation, 15.0)  # Cap at 15% additional
    
    # 5. Application type
    app_factor = {
        "E-bike": 1.0,
        "E-car": 1.3  # Higher stress from intensive cycling
    }.get(survey_data.primary_application, 1.0)
    
    total_degradation = (years_degradation + usage_degradation + 
                        charging_degradation + temp_degradation)
    app_adjustment = total_degradation * (app_factor - 1.0) * 0.5
    soh -= app_adjustment
    
    # Clamp SOH to 0-100%
    soh = max(0, min(100, soh))
    
    # Calculate confidence score
    # Higher confidence for longer ownership (more data points)
    base_confidence = 70 + (survey_data.years_owned * 5)
    
    # Adjust confidence based on usage patterns
    if survey_data.years_owned == 0:
        confidence = 95  # New battery - high confidence
    elif survey_data.years_owned >= 3:
        confidence = min(85, base_confidence)  # Mature data
    else:
        confidence = min(80, base_confidence)
    
    # Build explanation
    total_loss = 100 - soh
    explanation = f"""
Battery Condition Analysis (Heuristic-Based Prediction)

Input Summary:
- Battery: {survey_data.brand_model}
- Initial Capacity: {survey_data.initial_capacity} Ahr
- Ownership: {survey_data.years_owned} years
- Primary Use: {survey_data.primary_application}
- Daily Usage: {survey_data.avg_daily_usage}
- Charging Pattern: {survey_data.typical_charge_level}
- Operating Temp: {survey_data.avg_temperature}°C

Degradation Analysis:
1. Time-based aging: {years_degradation:.1f}% (2.5% per year baseline)
2. Usage intensity: {usage_degradation:.1f}% ({survey_data.avg_daily_usage.lower()} = {usage_factor}% per year)
3. Charging pattern: {charging_degradation:.1f}% ({survey_data.typical_charge_level} pattern)
4. Temperature impact: {temp_degradation:.1f}% (offset from 25°C baseline)
5. Application impact: {app_adjustment:.1f}% (E-car has higher stress)

Total Estimated Degradation: {total_loss:.1f}%
Predicted State of Health (SOH): {soh:.1f}%

Predicted Current Capacity: {survey_data.initial_capacity * (soh/100):.2f} Ahr

Confidence: {confidence}% (higher = more reliable)
- New batteries (<1 year): Very high confidence
- Established patterns (2-5 years): High confidence  
- Very old batteries (>5 years): Medium confidence (unpredictable degradation)

This prediction is based on typical Li-ion degradation patterns.
Actual capacity may vary based on storage conditions and usage cycles.
"""
    
    return {
        "predicted_capacity": survey_data.initial_capacity * (soh / 100),
        "confidence": confidence,
        "explanation": explanation,
        "soh_percentage": soh,
        "total_degradation_percent": total_loss
    }


def call_gemini_api(prompt: str) -> Dict:
    """
    Call Gemini API with fallback to alternate API keys if one fails.
    
    Args:
        prompt: The prompt to send to Gemini API
        
    Returns:
        Dict with 'predicted_capacity', 'confidence', and 'explanation'
    """
    api_keys = [
        os.getenv(f"GEMINI_API_KEY_{i}") 
        for i in range(1, 6) 
        if os.getenv(f"GEMINI_API_KEY_{i}")
    ]
    
    if not api_keys:
        raise ValueError("No Gemini API keys found in environment variables")
    
    # Using the standard Gemini model endpoint
    gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.0-pro:generateContent"
    
    for attempt, api_key in enumerate(api_keys, 1):
        try:
            headers = {
                "Content-Type": "application/json"
            }
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(
                f"{gemini_url}?key={api_key}",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                # Extract text from Gemini response
                try:
                    generated_text = response_data['candidates'][0]['content']['parts'][0]['text']
                    return {
                        "generated_text": generated_text,
                        "api_key_index": attempt
                    }
                except (KeyError, IndexError) as e:
                    raise ValueError(f"Unexpected response format from Gemini API: {str(e)}")
            
            elif response.status_code == 429:
                # Rate limit error - try next key
                continue
            elif response.status_code == 401:
                # Invalid API key - try next one
                continue
            else:
                raise ValueError(f"API error {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            if attempt == len(api_keys):
                raise ValueError(f"All API keys failed. Last error: {str(e)}")
            continue
    
    raise ValueError(f"All {len(api_keys)} Gemini API keys failed or rate limited")


def parse_gemini_response(gemini_text: str) -> Dict:
    """
    Parse Gemini API response to extract predicted capacity, confidence, and explanation.
    
    Args:
        gemini_text: Text response from Gemini API
        
    Returns:
        Dict with 'predicted_capacity', 'confidence', 'explanation'
    """
    import re
    
    # Initialize defaults
    predicted_capacity = None
    confidence = 70.0
    explanation = gemini_text
    
    # Try to extract predicted capacity (look for patterns like "2.5 Ahr", "2.5 Ah", etc.)
    capacity_patterns = [
        r"predicted.*?capacity[:\s]+([0-9.]+)\s*Ahr?",
        r"current.*?capacity[:\s]+([0-9.]+)\s*Ahr?",
        r"Capacity[:\s]+([0-9.]+)\s*Ahr?",
        r"([0-9.]+)\s*Ahr?",  # Fallback to any decimal followed by Ahr/Ah
    ]
    
    for pattern in capacity_patterns:
        match = re.search(pattern, gemini_text, re.IGNORECASE)
        if match:
            predicted_capacity = float(match.group(1))
            break
    
    # Try to extract confidence (look for percentage)
    confidence_pattern = r"confidence[:\s]+([0-9.]+)\s*%?"
    confidence_match = re.search(confidence_pattern, gemini_text, re.IGNORECASE)
    if confidence_match:
        confidence = float(confidence_match.group(1))
        if confidence > 100:
            confidence = 100
    
    if predicted_capacity is None:
        raise ValueError("Could not extract predicted capacity from Gemini response")
    
    return {
        "predicted_capacity": predicted_capacity,
        "confidence": confidence,
        "explanation": gemini_text
    }


@router.post("/predict-capacity-survey", response_model=CapacityPredictionResponse)
async def predict_capacity_from_survey(survey_data: UserSurveyInput):
    """
    Predict battery current capacity based on user survey responses using heuristic algorithm.
    
    This endpoint takes user-provided information about battery usage patterns and history,
    then uses a statistical degradation model to predict the likely current capacity of the battery.
    No external API required - uses local calculation.
    
    Args:
        survey_data: User survey with battery information and usage patterns
        
    Returns:
        CapacityPredictionResponse: Predicted capacity, confidence, and explanation
    """
    try:
        # Calculate degradation using local heuristic model
        prediction = calculate_battery_degradation(survey_data)
        
        return CapacityPredictionResponse(
            success=True,
            predicted_current_capacity=round(prediction['predicted_capacity'], 2),
            confidence=min(100, max(0, prediction['confidence'])),
            explanation=prediction['explanation'].strip(),
            input_summary={
                "brand_model": survey_data.brand_model,
                "initial_capacity_ahr": survey_data.initial_capacity,
                "years_owned": survey_data.years_owned,
                "primary_application": survey_data.primary_application,
                "avg_daily_usage": survey_data.avg_daily_usage,
                "charging_frequency_per_week": survey_data.charging_frequency_in_week,
                "typical_charge_level": survey_data.typical_charge_level,
                "avg_temperature_c": survey_data.avg_temperature,
                "method": "Heuristic Degradation Model (No External API)",
                "soh_percentage": round(prediction['soh_percentage'], 1),
                "total_degradation_percent": round(prediction['total_degradation_percent'], 1)
            }
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Capacity prediction error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error during prediction: {str(e)}")


# Import metadata at module level for use in endpoints
from pathlib import Path
import json

metadata_path = Path(__file__).parent.parent.parent / "modelTraining" / "model_metadata.json"
with open(str(metadata_path), 'r') as f:
    metadata = json.load(f)