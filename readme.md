## Frontend - https://github.com/SOMASEKAR17/voltage-chain-frontend
## Server1 - https://github.com/SOMASEKAR17/voltage-chain-server1
## Server2 - https://github.com/SOMASEKAR17/voltage-chain-server2

# Battery NFT Marketplace – ML Service (FastAPI)

## Overview

This microservice handles:

- Battery history retrieval
- Voltage prediction using ML model
- Questionnaire-based fallback prediction

---

## Flow

1. Express sends:
   - Battery code
   - Brand
   - Years used
   - Initial voltage

2. Service checks:
   - Historical database
   - If found → return history
   - If not → return null

3. Predict current voltage

4. If voltage not provided:
   - Use questionnaire model
   - Predict voltage from behavioral data

---

## Endpoints

POST /predict-voltage  
POST /predict-from-questionnaire  
GET /history/{battery_code}/{brand}

---

## Run

uvicorn app.main:app --reload

---

## Models

- voltage_model.pkl → Regression model
- questionnaire_model.pkl → Classification/regression hybrid

---

## Future Improvements

- Continuous learning from marketplace data
- Anomaly detection
- Fraud probability scoring
