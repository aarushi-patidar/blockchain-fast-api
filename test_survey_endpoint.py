"""
Test script for the new survey-based battery capacity prediction endpoint
"""
import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_capacity_prediction():
    """Test the predict-capacity-survey endpoint"""
    
    # Example survey data
    survey_data = {
        "listing_id": "550e8400-e29b-41d4-a716-446655440000",
        "brand_model": "Samsung 18650 INR18650-30Q",
        "initial_capacity": 3.0,
        "years_owned": 2,
        "primary_application": "E-bike",
        "avg_daily_usage": "Medium",
        "charging_frequency_in_week": 4,
        "typical_charge_level": "20-80",
        "avg_temperature": 25.0
    }
    
    try:
        print("=" * 60)
        print("Testing Survey-Based Battery Capacity Prediction")
        print("=" * 60)
        print("\nSending request to /api/predict-capacity-survey")
        print(f"\nSurvey Data:")
        print(json.dumps(survey_data, indent=2))
        
        response = requests.post(
            f"{BASE_URL}/predict-capacity-survey",
            json=survey_data,
            timeout=60
        )
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\nPrediction Results:")
            print(f"  Success: {result['success']}")
            print(f"  Predicted Current Capacity: {result['predicted_current_capacity']} Ahr")
            print(f"  Confidence: {result['confidence']}%")
            print(f"\nExplanation:")
            print(f"  {result['explanation']}")
            print(f"\nInput Summary:")
            print(json.dumps(result['input_summary'], indent=2))
        else:
            print(f"\nError Response:")
            print(response.json())
        
        print("\n" + "=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to the API server.")
        print("Make sure the FastAPI server is running on http://localhost:8000")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    test_capacity_prediction()
