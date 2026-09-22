#!/bin/bash
# Quick test commands for the Survey-Based Battery Capacity Prediction endpoint

echo "=================================="
echo "Survey-Based Capacity Prediction Tests"
echo "=================================="
echo ""

# Test 1: Example with medium usage
echo "Test 1: Medium usage, 20-80 charging (Conservative)"
echo "-----"
curl -X POST "http://localhost:8000/api/predict-capacity-survey" \
  -H "Content-Type: application/json" \
  -d '{
    "listing_id": "550e8400-e29b-41d4-a716-446655440000",
    "brand_model": "Samsung 18650 INR18650-30Q",
    "initial_capacity": 3.0,
    "years_owned": 2,
    "primary_application": "E-bike",
    "avg_daily_usage": "Medium",
    "charging_frequency_in_week": 4,
    "typical_charge_level": "20-80",
    "avg_temperature": 25.0
  }' | jq '.'

echo ""
echo ""

# Test 2: Heavy usage, 0-100 charging (Aggressive)
echo "Test 2: Heavy usage, 0-100 charging (Aggressive, higher degradation)"
echo "-----"
curl -X POST "http://localhost:8000/api/predict-capacity-survey" \
  -H "Content-Type: application/json" \
  -d '{
    "listing_id": "550e8400-e29b-41d4-a716-446655440001",
    "brand_model": "LG MJ1 18650",
    "initial_capacity": 3.5,
    "years_owned": 3,
    "primary_application": "E-car",
    "avg_daily_usage": "Heavy",
    "charging_frequency_in_week": 7,
    "typical_charge_level": "0-100",
    "avg_temperature": 35.0
  }' | jq '.'

echo ""
echo ""

# Test 3: Light usage with high temperature stress
echo "Test 3: Light usage but high temperature (50°C) stress"
echo "-----"
curl -X POST "http://localhost:8000/api/predict-capacity-survey" \
  -H "Content-Type: application/json" \
  -d '{
    "listing_id": "550e8400-e29b-41d4-a716-446655440002",
    "brand_model": "Panasonic NCR18650B",
    "initial_capacity": 3.4,
    "years_owned": 1,
    "primary_application": "E-bike",
    "avg_daily_usage": "Light",
    "charging_frequency_in_week": 2,
    "typical_charge_level": "20-80",
    "avg_temperature": 50.0
  }' | jq '.'

echo ""
echo ""

# Test 4: New battery with minimal usage
echo "Test 4: Nearly new battery (6 months, light usage)"
echo "-----"
curl -X POST "http://localhost:8000/api/predict-capacity-survey" \
  -H "Content-Type: application/json" \
  -d '{
    "listing_id": "550e8400-e29b-41d4-a716-446655440003",
    "brand_model": "Sony US18650VTC6",
    "initial_capacity": 3.0,
    "years_owned": 0,
    "primary_application": "E-bike",
    "avg_daily_usage": "Light",
    "charging_frequency_in_week": 1,
    "typical_charge_level": "20-80",
    "avg_temperature": 22.0
  }' | jq '.'

echo ""
echo ""

# Test 5: Very old battery with always-full charging (worst case)
echo "Test 5: Old battery (5 years) with always-full charging (worst case)"
echo "-----"
curl -X POST "http://localhost:8000/api/predict-capacity-survey" \
  -H "Content-Type: application/json" \
  -d '{
    "listing_id": "550e8400-e29b-41d4-a716-446655440004",
    "brand_model": "Generic 18650",
    "initial_capacity": 2.8,
    "years_owned": 5,
    "primary_application": "E-car",
    "avg_daily_usage": "Heavy",
    "charging_frequency_in_week": 10,
    "typical_charge_level": "Always Full",
    "avg_temperature": 30.0
  }' | jq '.'

echo ""
echo "=================================="
echo "Tests complete!"
echo "=================================="
echo ""
echo "Notes:"
echo "- Make sure the FastAPI server is running (python run.py)"
echo "- Make sure .env is configured with valid Gemini API keys"
echo "- The 'jq' command is used for pretty-printing JSON (install with: apt-get install jq)"
echo "- If jq is not available, remove '| jq .' at the end of curl commands"
