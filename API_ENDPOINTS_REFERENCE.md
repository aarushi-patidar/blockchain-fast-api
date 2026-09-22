# Voltage Chain Battery Prediction API - Complete Endpoints Reference

## Overview

The FastAPI server provides 5 battery analysis and prediction endpoints plus health check.

**Base URL:** `http://localhost:8000/api`

---

## All Endpoints Summary

| Method | Endpoint                          | Purpose                              | Response                                    |
| ------ | --------------------------------- | ------------------------------------ | ------------------------------------------- |
| `GET`  | `/health`                         | Health check                         | Status message                              |
| `POST` | `/predict-rul`                    | RUL prediction from cycle data       | RUL cycles, health, recommendations         |
| `GET`  | `/health-status/{soh_percentage}` | Health status lookup                 | Status category, description                |
| `GET`  | `/test-prediction`                | Test RUL with example data           | Example prediction response                 |
| `POST` | `/predict-capacity-survey`        | **NEW** AI-based capacity prediction | Predicted capacity, confidence, explanation |

---

## Endpoint Details

### 1. Health Check

```
GET /api/health
```

**Description:** Check if API is running

**Response:**

```json
{
  "status": "ok",
  "message": "Battery Prediction API is healthy ✅"
}
```

---

### 2. RUL Prediction (Cycle-Based)

```
POST /api/predict-rul
```

**Description:** Predict Remaining Useful Life from battery metrics

**Request Body:**

```json
{
  "current_capacity": 2.0,
  "initial_capacity": 3.0,
  "ambient_temperature": 25.0,
  "cycle_count": 40,
  "age_days": 300
}
```

**Response:**

```json
{
  "success": true,
  "battery_metrics": {
    "initial_capacity_ahr": 3.0,
    "current_capacity_ahr": 2.0,
    "cycle_count": 40,
    "age_days": 300,
    "ambient_temperature_c": 25.0
  },
  "health_analysis": {
    "soh_percentage": 66.7,
    "health_status": "POOR",
    "health_description": "Significant degradation, limited lifespan",
    "degradation_factor_percent": 33.3
  },
  "rul_prediction": {
    "rul_cycles": 51,
    "estimated_days_to_eol": 385,
    "estimated_time_to_eol": "385 days (~12.8 months)"
  },
  "recommendations": ["Limit to non-critical backup applications..."]
}
```

**Use Case:** When you have measured battery metrics and cycle data

---

### 3. Health Status Lookup

```
GET /api/health-status/{soh_percentage}
```

**Description:** Get health category for a given State of Health percentage

**Path Parameters:**

- `soh_percentage`: Float (0-100)

**Example:** `GET /api/health-status/66.7`

**Response:**

```json
{
  "soh_percentage": 66.7,
  "health_status": "POOR",
  "health_description": "Significant degradation, limited lifespan"
}
```

**Health Categories:**

- EXCELLENT (95-100%): New or near-new condition
- GOOD (85-94%): Minimal degradation
- FAIR (70-84%): Noticeable degradation
- POOR (60-69%): Significant degradation
- CRITICAL (0-59%): Near end-of-life

---

### 4. Test Prediction

```
GET /api/test-prediction
```

**Description:** Test RUL endpoint with pre-configured example data

**Example Data:**

- Current Capacity: 2.0 Ahr
- Initial Capacity: 3.0 Ahr
- Cycle Count: 40
- Age: 300 days
- Temperature: 29°C

**Response:** Same as `/predict-rul` with example data

**Use Case:** Quick API test without providing data

---

### 5. Survey-Based Capacity Prediction ⭐ NEW

```
POST /api/predict-capacity-survey
```

**Description:** Predict battery current capacity using Gemini AI analysis of usage survey

**Request Body:**

```json
{
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
```

**Response:**

```json
{
    "success": true,
    "predicted_current_capacity": 10.61,
    "confidence": 80.0,
    "explanation": "Battery Condition Analysis (Heuristic-Based Prediction)\n\nInput Summary:\n- Battery: Samsung 18650 INR18650-30Q\n- Initial Capacity: 12.0 Ahr\n- Ownership: 2 years\n- Primary Use: E-car\n- Daily Usage: Medium\n- Charging Pattern: 20-80\n- Operating Temp: 25.0°C\n\nDegradation Analysis:\n1. Time-based aging: 5.0% (2.5% per year baseline)\n2. Usage intensity: 3.0% (medium = 1.5% per year)\n3. Charging pattern: 0.6% (20-80 pattern)\n4. Temperature impact: 1.5% (offset from 25°C baseline)\n5. Application impact: 1.5% (E-car has higher stress)\n\nTotal Estimated Degradation: 11.6%\nPredicted State of Health (SOH): 88.4%\n\nPredicted Current Capacity: 10.61 Ahr\n\nConfidence: 80% (higher = more reliable)\n- New batteries (<1 year): Very high confidence\n- Established patterns (2-5 years): High confidence  \n- Very old batteries (>5 years): Medium confidence (unpredictable degradation)\n\nThis prediction is based on typical Li-ion degradation patterns.\nActual capacity may vary based on storage conditions and usage cycles.",
    "input_summary": {
        "brand_model": "Samsung 18650 INR18650-30Q",
        "initial_capacity_ahr": 12.0,
        "years_owned": 2,
        "primary_application": "E-car",
        "avg_daily_usage": "Medium",
        "charging_frequency_per_week": 4,
        "typical_charge_level": "20-80",
        "avg_temperature_c": 25.0,
        "method": "Heuristic Degradation Model (No External API)",
        "soh_percentage": 88.4,
        "total_degradation_percent": 11.6
    }
}
```

**Use Case:** Predict current capacity from owner survey (no measurements needed)

---

## 🔗 Workflow Examples

### Workflow 1: Direct Measurement Available

```
User has measured battery metrics
    ↓
Call POST /api/predict-rul
    ↓
Get RUL prediction + health status
    ↓
Display recommendations
```

### Workflow 2: Only Survey Data Available

```
User completes survey (brand, usage, age, etc.)
    ↓
Call POST /api/predict-capacity-survey
    ↓
Get predicted current capacity
    ↓
(Optional) Use capacity in POST /api/predict-rul
    ↓
Get complete analysis
```

### Workflow 3: Health Status Check

```
User wants to know health category
    ↓
Call GET /api/health-status/{soh_percentage}
    ↓
Get health category + description
```

---

## 📊 Comparison: RUL vs Survey Endpoint

| Aspect           | `/predict-rul`                 | `/predict-capacity-survey`  |
| ---------------- | ------------------------------ | --------------------------- |
| Input Type       | Measured metrics               | User survey                 |
| Required Params  | 5 (cycle count, age, capacity) | 9 (usage history, app type) |
| Data Needed      | Actual measurements            | User report                 |
| Accuracy         | High (based on real data)      | Medium-High (AI estimate)   |
| Confidence       | Implicit (model R²=0.92)       | Explicit (0-100% score)     |
| AI Used          | XGBoost model                  | Google Gemini               |
| Response Time    | <1 second                      | 3-5 seconds                 |
| Requires API Key | No                             | Yes (Gemini)                |

**Recommendation:**

- Use `/predict-rul` if you have actual measurements
- Use `/predict-capacity-survey` if you only have user information

---

## 🔄 Combined Workflow (Recommended)

For best results, combine both endpoints:

```python
# Step 1: Get predicted current capacity from survey
survey_response = POST /api/predict-capacity-survey
predicted_capacity = survey_response['predicted_current_capacity']

# Step 2: Use predicted capacity with RUL prediction
rul_request = {
    "current_capacity": predicted_capacity,
    "initial_capacity": survey_response['input_summary']['initial_capacity_ahr'],
    "cycle_count": 40,  # Estimated
    "age_days": survey_response['input_summary']['years_owned'] * 365,
    "ambient_temperature": 25.0
}
rul_response = POST /api/predict-rul(rul_request)

# Step 3: Get complete analysis
print(f"Predicted Capacity: {predicted_capacity} Ahr")
print(f"Health Status: {rul_response['health_analysis']['health_status']}")
print(f"RUL: {rul_response['rul_prediction']['rul_cycles']} cycles")
```

---

## ⚡ Performance Characteristics

| Endpoint                   | Response Time | Server Load | Dependencies  |
| -------------------------- | ------------- | ----------- | ------------- |
| `/health`                  | <10ms         | Very Low    | None          |
| `/predict-rul`             | <100ms        | Low         | XGBoost local |
| `/health-status/{soh}`     | <10ms         | Very Low    | None          |
| `/test-prediction`         | <100ms        | Low         | XGBoost local |
| `/predict-capacity-survey` | 3-5s          | Medium      | Gemini API    |

**Note:** `/predict-capacity-survey` is slower due to external API call.

---

## 🛡️ Error Handling

### Status Codes

| Code | Meaning                         | Endpoint                   |
| ---- | ------------------------------- | -------------------------- |
| 200  | Success                         | All endpoints              |
| 400  | Bad request / Prediction failed | All POST/GET with params   |
| 401  | Unauthorized (invalid API key)  | `/predict-capacity-survey` |
| 422  | Validation error                | All POST endpoints         |
| 500  | Server error                    | All endpoints              |

### Example Error Response

```json
{
  "detail": "Capacity prediction error: All 5 Gemini API keys failed or are rate limited"
}
```

---

## 🧪 Quick Test Commands

### Test All Endpoints

```bash
# Health check
curl http://localhost:8000/api/health

# RUL prediction
curl -X POST http://localhost:8000/api/predict-rul \
  -H "Content-Type: application/json" \
  -d '{"current_capacity":2,"initial_capacity":3,"cycle_count":40,"age_days":300}'

# Health status
curl http://localhost:8000/api/health-status/66.7

# Test prediction
curl http://localhost:8000/api/test-prediction

# Survey-based prediction
curl -X POST http://localhost:8000/api/predict-capacity-survey \
  -H "Content-Type: application/json" \
  -d '{
    "listing_id":"550e8400-e29b-41d4-a716-446655440000",
    "brand_model":"Samsung 18650",
    "initial_capacity":3.0,
    "years_owned":2,
    "primary_application":"E-bike",
    "avg_daily_usage":"Medium",
    "charging_frequency_in_week":4,
    "typical_charge_level":"20-80",
    "avg_temperature":25
  }'
```

---

## 📖 Documentation Files

Each endpoint has detailed documentation:

| File                               | Content                  |
| ---------------------------------- | ------------------------ |
| `API_DOCUMENTATION.md`             | RUL endpoint details     |
| `SURVEY_ENDPOINT_DOCUMENTATION.md` | Survey endpoint details  |
| `SETUP_GUIDE.md`                   | Setup and integration    |
| `IMPLEMENTATION_SUMMARY.md`        | Technical implementation |

---

## 🎯 Which Endpoint Should I Use?

**Choose `/predict-rul` if:**

- ✅ You have measured battery data
- ✅ You know current capacity
- ✅ You want fastest response
- ✅ Battery is currently in use

**Choose `/predict-capacity-survey` if:**

- ✅ Battery owner is selling/listing it
- ✅ You only have descriptive info (usage history)
- ✅ Accurate measurements unavailable
- ✅ You want AI-powered estimation

**Use both together for:**

- ✅ Complete battery health assessment
- ✅ Comparison of methods
- ✅ Cross-validation of capacity estimate

---

## 🔐 API Key Management (Survey Endpoint Only)

The `/predict-capacity-survey` endpoint uses 5 API keys for fallback:

```env
GEMINI_API_KEY_1=key1
GEMINI_API_KEY_2=key2
GEMINI_API_KEY_3=key3
GEMINI_API_KEY_4=key4
GEMINI_API_KEY_5=key5
```

**Fallback Logic:**

1. Try KEY_1
2. If fails (rate limit/error) → Try KEY_2
3. Continue through KEY_5
4. If all fail → Return error

Response includes which key was used: `"api_key_used": "Key #2"`

---

## 📈 Scalability Notes

- RUL endpoints: Highly scalable (in-process ML)
- Survey endpoint: Limited by Gemini API quotas
- All endpoints: Stateless (no database required initially)
- Recommendation: Add caching for frequently requested surveys

---

_Last Updated: February 14, 2026_
_API Version: 2.1 (with Survey Endpoint)_
