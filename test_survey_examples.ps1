# Quick test commands for the Survey-Based Battery Capacity Prediction endpoint (Windows PowerShell)

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Survey-Based Capacity Prediction Tests" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Example with medium usage
Write-Host "Test 1: Medium usage, 20-80 charging (Conservative)" -ForegroundColor Yellow
Write-Host "-----" -ForegroundColor Yellow

$body1 = @{
    listing_id = "550e8400-e29b-41d4-a716-446655440000"
    brand_model = "Samsung 18650 INR18650-30Q"
    initial_capacity = 3.0
    years_owned = 2
    primary_application = "E-bike"
    avg_daily_usage = "Medium"
    charging_frequency_in_week = 4
    typical_charge_level = "20-80"
    avg_temperature = 25.0
} | ConvertTo-Json

$response1 = Invoke-WebRequest -Uri "http://localhost:8000/api/predict-capacity-survey" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body $body1

$response1.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10 | Write-Host

Write-Host ""
Write-Host ""

# Test 2: Heavy usage, 0-100 charging (Aggressive)
Write-Host "Test 2: Heavy usage, 0-100 charging (Aggressive, higher degradation)" -ForegroundColor Yellow
Write-Host "-----" -ForegroundColor Yellow

$body2 = @{
    listing_id = "550e8400-e29b-41d4-a716-446655440001"
    brand_model = "LG MJ1 18650"
    initial_capacity = 3.5
    years_owned = 3
    primary_application = "E-car"
    avg_daily_usage = "Heavy"
    charging_frequency_in_week = 7
    typical_charge_level = "0-100"
    avg_temperature = 35.0
} | ConvertTo-Json

$response2 = Invoke-WebRequest -Uri "http://localhost:8000/api/predict-capacity-survey" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body $body2

$response2.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10 | Write-Host

Write-Host ""
Write-Host ""

# Test 3: Light usage with high temperature stress
Write-Host "Test 3: Light usage but high temperature (50°C) stress" -ForegroundColor Yellow
Write-Host "-----" -ForegroundColor Yellow

$body3 = @{
    listing_id = "550e8400-e29b-41d4-a716-446655440002"
    brand_model = "Panasonic NCR18650B"
    initial_capacity = 3.4
    years_owned = 1
    primary_application = "E-bike"
    avg_daily_usage = "Light"
    charging_frequency_in_week = 2
    typical_charge_level = "20-80"
    avg_temperature = 50.0
} | ConvertTo-Json

$response3 = Invoke-WebRequest -Uri "http://localhost:8000/api/predict-capacity-survey" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body $body3

$response3.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10 | Write-Host

Write-Host ""
Write-Host ""

# Test 4: New battery with minimal usage
Write-Host "Test 4: Nearly new battery (6 months, light usage)" -ForegroundColor Yellow
Write-Host "-----" -ForegroundColor Yellow

$body4 = @{
    listing_id = "550e8400-e29b-41d4-a716-446655440003"
    brand_model = "Sony US18650VTC6"
    initial_capacity = 3.0
    years_owned = 0
    primary_application = "E-bike"
    avg_daily_usage = "Light"
    charging_frequency_in_week = 1
    typical_charge_level = "20-80"
    avg_temperature = 22.0
} | ConvertTo-Json

$response4 = Invoke-WebRequest -Uri "http://localhost:8000/api/predict-capacity-survey" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body $body4

$response4.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10 | Write-Host

Write-Host ""
Write-Host ""

# Test 5: Very old battery with always-full charging (worst case)
Write-Host "Test 5: Old battery (5 years) with always-full charging (worst case)" -ForegroundColor Yellow
Write-Host "-----" -ForegroundColor Yellow

$body5 = @{
    listing_id = "550e8400-e29b-41d4-a716-446655440004"
    brand_model = "Generic 18650"
    initial_capacity = 2.8
    years_owned = 5
    primary_application = "E-car"
    avg_daily_usage = "Heavy"
    charging_frequency_in_week = 10
    typical_charge_level = "Always Full"
    avg_temperature = 30.0
} | ConvertTo-Json

$response5 = Invoke-WebRequest -Uri "http://localhost:8000/api/predict-capacity-survey" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body $body5

$response5.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10 | Write-Host

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Tests complete!" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Notes:" -ForegroundColor Green
Write-Host "- Make sure the FastAPI server is running (python run.py)" -ForegroundColor Green
Write-Host "- Make sure .env is configured with valid Gemini API keys" -ForegroundColor Green
Write-Host "- If tests fail, check server logs for error details" -ForegroundColor Green
