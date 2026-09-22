# Survey-Based Battery Capacity Prediction Endpoint

## Overview

The `/api/predict-capacity-survey` endpoint uses the Gemini AI API to predict a battery's current capacity based on user survey responses about the battery's history, usage patterns, and operating conditions.

## Endpoint Details

**Route:** `POST /api/predict-capacity-survey`

**Description:** Predicts battery current capacity using Gemini AI analysis of user survey data

---

## Request Schema

### UserSurveyInput Model

```json
{
  "listing_id": "string (UUID format)",
  "brand_model": "string (e.g., 'Samsung 18650 INR18650-30Q')",
  "initial_capacity": "number (> 0, in Ahr)",
  "years_owned": "integer (>= 0)",
  "primary_application": "string ('E-bike' or 'E-car')",
  "avg_daily_usage": "string ('Light', 'Medium', or 'Heavy')",
  "charging_frequency_in_week": "integer (>= 0)",
  "typical_charge_level": "string ('20-80', '0-100', or 'Always Full')",
  "avg_temperature": "number (optional, default: 25.0, in °C)"
}
```

### Field Descriptions

| Field                        | Type          | Required | Example                                | Description                                                 |
| ---------------------------- | ------------- | -------- | -------------------------------------- | ----------------------------------------------------------- |
| `listing_id`                 | string (UUID) | ✅ Yes   | `550e8400-e29b-41d4-a716-446655440000` | Unique identifier for the battery listing                   |
| `brand_model`                | string        | ✅ Yes   | `Samsung 18650 INR18650-30Q`           | Battery brand and model number                              |
| `initial_capacity`           | float         | ✅ Yes   | `3.0`                                  | Original/rated capacity in Ampere-hours                     |
| `years_owned`                | integer       | ✅ Yes   | `2`                                    | How long the battery has been owned                         |
| `primary_application`        | string        | ✅ Yes   | `E-bike`                               | Primary use case: 'E-bike' or 'E-car'                       |
| `avg_daily_usage`            | string        | ✅ Yes   | `Medium`                               | Daily usage intensity: 'Light', 'Medium', or 'Heavy'        |
| `charging_frequency_in_week` | integer       | ✅ Yes   | `4`                                    | How many times per week the battery is charged              |
| `typical_charge_level`       | string        | ✅ Yes   | `20-80`                                | Typical charging window: '20-80', '0-100', or 'Always Full' |
| `avg_temperature`            | float         | ❌ No    | `25.0`                                 | Average operating temperature in Celsius (default: 25°C)    |

---

## Request Example

```bash
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
  }'
```

---

## Response Schema

### CapacityPredictionResponse Model

```json
{
  "success": true,
  "predicted_current_capacity": 2.45,
  "confidence": 82.5,
  "explanation": "Based on 2 years of medium usage with conservative 20-80 charging...",
  "input_summary": {
    "brand_model": "Samsung 18650 INR18650-30Q",
    "initial_capacity_ahr": 3.0,
    "years_owned": 2,
    "primary_application": "E-bike",
    "avg_daily_usage": "Medium",
    "charging_frequency_per_week": 4,
    "typical_charge_level": "20-80",
    "avg_temperature_c": 25.0,
    "api_key_used": "Key #1"
  }
}
```

### Response Fields

| Field                        | Type    | Description                                               |
| ---------------------------- | ------- | --------------------------------------------------------- |
| `success`                    | boolean | Whether the prediction was successful                     |
| `predicted_current_capacity` | float   | Estimated current capacity in Ahr (rounded to 2 decimals) |
| `confidence`                 | float   | Confidence score of the prediction (0-100%)               |
| `explanation`                | string  | Detailed analysis from Gemini explaining the prediction   |
| `input_summary`              | object  | Echo of input data and which API key was used             |

---

## Response Example

```json
{
  "success": true,
  "predicted_current_capacity": 2.45,
  "confidence": 82.5,
  "explanation": "Based on the survey data provided:\n\n- The Samsung 18650 INR18650-30Q has an initial capacity of 3.0 Ahr\n- After 2 years of medium daily usage (4 charges per week)\n- With conservative 20-80% charging pattern (which extends battery life)\n- At typical 25°C operating temperature\n\nBased on typical Li-ion degradation rates:\n- Calendric aging: ~2-3% per year in moderate conditions\n- Cycle-based aging: minimal with 20-80 charging\n- Expected total degradation: ~15-20% over 2 years\n\nPredicted current capacity: ~2.45 Ahr (81.7% retention)\n\nThis is a conservative estimate favoring longevity given the good charging practices.",
  "input_summary": {
    "brand_model": "Samsung 18650 INR18650-30Q",
    "initial_capacity_ahr": 3.0,
    "years_owned": 2,
    "primary_application": "E-bike",
    "avg_daily_usage": "Medium",
    "charging_frequency_per_week": 4,
    "typical_charge_level": "20-80",
    "avg_temperature_c": 25.0,
    "api_key_used": "Key #1"
  }
}
```

---

## Error Responses

### 400 Bad Request

Returned when input validation fails or Gemini API cannot predict:

```json
{
  "detail": "Capacity prediction error: Could not extract predicted capacity from Gemini response"
}
```

### 401 Unauthorized

Returned when all Gemini API keys are invalid:

```json
{
  "detail": "Capacity prediction error: All 5 Gemini API keys failed or are rate limited"
}
```

### 500 Internal Server Error

Returned for unexpected server errors:

```json
{
  "detail": "Unexpected error during prediction: [error details]"
}
```

---

## API Key Configuration

The endpoint uses fallback API key handling. Configure API keys in `.env`:

```env
GEMINI_API_KEY_1=your_gemini_api_key_1
GEMINI_API_KEY_2=your_gemini_api_key_2
GEMINI_API_KEY_3=your_gemini_api_key_3
GEMINI_API_KEY_4=your_gemini_api_key_4
GEMINI_API_KEY_5=your_gemini_api_key_5
```

### How Fallback Works

1. The endpoint tries API_KEY_1
2. If it fails (rate limit, invalid, network error), it tries API_KEY_2
3. Continues through all 5 keys
4. Returns error only if all keys fail
5. Response indicates which key was successfully used (`api_key_used` field)

---

## Degradation Factors Considered

The Gemini AI analyzes the following when predicting capacity:

### 1. Time-Based Degradation

- How many years the battery has been owned
- Typical Li-ion degradation: 2-3% per year at room temperature

### 2. Usage-Based Degradation

- Daily usage intensity (Light, Medium, Heavy)
- Charging frequency per week
- Total approximate cycles (years_owned × frequency)

### 3. Charging Pattern Impact

- **20-80 charging**: Minimal degradation (preferred for longevity)
- **0-100 charging**: Moderate degradation
- **Always Full**: Maximum degradation (worst for battery health)

### 4. Temperature Effects

- Higher temperatures accelerate degradation significantly
- Each 10°C increase can roughly double degradation rate

### 5. Application Type

- E-bike batteries typically have moderate cycling
- E-car batteries have more intensive usage patterns

---

## Integration Examples

### Python

```python
import requests

url = "http://localhost:8000/api/predict-capacity-survey"

survey = {
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

response = requests.post(url, json=survey)
result = response.json()

if result['success']:
    print(f"Predicted Capacity: {result['predicted_current_capacity']} Ahr")
    print(f"Confidence: {result['confidence']}%")
    print(f"\n{result['explanation']}")
else:
    print(f"Error: {result.get('detail', 'Unknown error')}")
```

### JavaScript/Node.js

```javascript
const url = "http://localhost:8000/api/predict-capacity-survey";

const survey = {
  listing_id: "550e8400-e29b-41d4-a716-446655440000",
  brand_model: "Samsung 18650 INR18650-30Q",
  initial_capacity: 3.0,
  years_owned: 2,
  primary_application: "E-bike",
  avg_daily_usage: "Medium",
  charging_frequency_in_week: 4,
  typical_charge_level: "20-80",
  avg_temperature: 25.0,
};

fetch(url, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(survey),
})
  .then((res) => res.json())
  .then((data) => {
    if (data.success) {
      console.log(`Predicted: ${data.predicted_current_capacity} Ahr`);
      console.log(`Confidence: ${data.confidence}%`);
      console.log(data.explanation);
    } else {
      console.error(data.detail);
    }
  });
```

---

## Validation Rules

### Primary Application

Must be exactly: `'E-bike'` or `'E-car'`

### Avg Daily Usage

Must be one of: `'Light'`, `'Medium'`, `'Heavy'`

### Typical Charge Level

Must be one of: `'20-80'`, `'0-100'`, `'Always Full'`

### Numeric Fields

- `initial_capacity` must be > 0
- `years_owned` must be >= 0
- `charging_frequency_in_week` must be >= 0
- `avg_temperature` should be a reasonable operating temperature (typically -10 to 60°C)

---

## Notes

- Predictions are AI-based estimates, not absolute guarantees
- Confidence scores indicate reliability of the prediction (higher is better)
- The endpoint requires active internet connection for Gemini API calls
- Timeout is set to 30 seconds per API call
- All API keys are tried sequentially with automatic fallback
- The explanation field contains the full Gemini response with detailed analysis

---

## Testing the Endpoint

A test script is provided at `test_survey_endpoint.py`:

```bash
python test_survey_endpoint.py
```

Make sure the FastAPI server is running first:

```bash
python run.py
```

---

_Last Updated: February 14, 2026_
_Version: 1.0 - Initial Release with Gemini Integration_
