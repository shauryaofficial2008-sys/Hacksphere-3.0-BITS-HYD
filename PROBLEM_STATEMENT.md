# HackSphere 3.0: Smart Energy Microgrid & Demand Forecasting Engine

## 1. Problem Overview

Modern power grids are rapidly integrating dynamic, localized renewable energy storage to handle sudden load shifts and reduce blackout risks. Modern microgrids require real-time demand forecasting to switch seamlessly between Main Grid power and local battery storage.

The challenge is to build an end-to-end web application deployed on **Zoho Catalyst** that forecasts hourly energy demand for the next 24 hours, trains a predictive model using **Zoho Catalyst QuickML**, and triggers automated power-source transition signals between Main Grid power and Renewable Battery Storage.

## 2. Official Starter Kit

The official archive contains:
- `train_telemetry.csv`: historical training data with weather features and ground-truth `target_demand_kw`.
- `sample_test_input.csv`: test data with weather features and no target.
- `predict.py`: inference template.
- `test_eval.py`: pre-submission self-test.

Dataset inspected: 4,000 training rows and 1,000 test rows. Training columns are timestamp, ambient_temp_c, humidity_pct, solar_irradiance_wm2, target_demand_kw. Test rows omit target_demand_kw.

## 3. Key Requirements

1. Train and publish a demand forecasting regression model inside Zoho Catalyst QuickML.
2. Accept telemetry via live UI form or CSV uploads; clean and validate inputs.
3. Call the published QuickML endpoint for one hourly prediction per input row in a 24-hour forecast.
4. Apply threshold and time-based transition rules.
5. Host a responsive dashboard showing predicted load curves, grid states, battery state-of-charge, and overload alerts.

## 4. Recommended Catalyst Architecture

| Feature / Module | Catalyst Service | Description |
|---|---|---|
| Telemetry Ingestion | Slate + Stratus | Build UI forms; store uploaded CSV files in Stratus. |
| Preprocessing & API | AppSail / Functions | Parse timestamps, preprocess features, and handle API requests. |
| Forecasting Engine | QuickML | Train, optimize, deploy regression pipeline, and expose REST endpoint. |
| Transition Controller | Functions / AppSail | Evaluate predictions against dispatch rules and emit control signals. |
| Live Dashboard | Slate + Data Store / NoSQL | Render charts, grid state, and system logs. |

Onboarding guide: https://atmos26-catalyst-kit.onslate.in/

## 5. Dataset and Telemetry Schema

| Column | Type | Units / Format | Description |
|---|---|---|---|
| timestamp | String | YYYY-MM-DD HH:MM:SS | Hourly timestamp. |
| ambient_temp_c | Float | °C | Outdoor ambient temperature. |
| humidity_pct | Float | % | Relative humidity. |
| solar_irradiance_wm2 | Float | W/m² | Solar power potential. |
| target_demand_kw | Float | kW | Ground-truth training target only; omitted from test inputs. |

### Inference Contract
- Supply one feature row for each forecast hour (24 rows for a full forecast).
- Each row includes timestamp and the three weather features.
- QuickML returns one numerical prediction per row.
- Any custom lag/rolling features must be created consistently for training and inference.

## 6. Transition Controller Logic

The 18:00–22:00 window is inclusive.

| Condition | Grid Mode / Alert |
|---|---|
| Demand >160 kW OR timestamp hour 18 through 22 inclusive | Renewable Storage Mode |
| Otherwise (demand <=160 kW and outside window) | Main Grid Mode |
| Demand >=200 kW | Critical Overload Alert, independent of grid mode |

## 7. Evaluation Criteria

| Criteria | Weight |
|---|---:|
| Model Accuracy (QuickML RMSE on hidden test data) | 35% |
| Deployment & Functionality (public Catalyst app) | 35% |
| Transition Controller Logic | 20% |
| UI & User Experience | 10% |

## 8. Local Testing

Run:
```bash
python predict.py --input sample_test_input.csv --output predictions.csv
python test_eval.py
```

Expected prediction CSV columns: `timestamp,target_demand_kw`, preserving the original input timestamp and producing exactly one prediction per row.

## 9. Submission Deliverables

1. Public Catalyst application URL.
2. Public GitHub repository or zipped source.
3. Full frontend/backend source, `predict.py` configured with the published QuickML endpoint, and README with setup and environment variables. Keep credentials secure.
