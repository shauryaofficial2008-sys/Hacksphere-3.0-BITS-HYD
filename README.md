# GridPulse — Smart Energy Microgrid & Demand Forecasting Engine

**HackSphere 3.0 · BITS Hyderabad**

GridPulse is a 24-hour energy demand forecasting and microgrid dispatch application. It combines a responsive dashboard, Python API, Zoho Catalyst QuickML inference adapter, telemetry CSV ingestion, and the HackSphere transition-controller rules.

## Official starter kit

The official `HackSphere_Starter_Kit.zip` :
- `train_telemetry.csv`: 4,000 historical rows with `target_demand_kw`.
- `sample_test_input.csv`: 1,000 feature-only test rows.
- `predict.py` and `test_eval.py`: official inference and evaluator contract.
- `PROBLEM_STATEMENT.md`: full challenge specification.

The training data columns are `timestamp`, `ambient_temp_c`, `humidity_pct`, `solar_irradiance_wm2`, and `target_demand_kw`. The target is excluded from inference.

## Application features

- Responsive energy operations dashboard with hourly load chart and dispatch timeline.
- Exactly 24 feature rows per dashboard forecast request.
- CSV telemetry upload and validation.
- QuickML inference adapter; explicit `DEMO_FALLBACK` label when no published endpoint is configured.
- Source switching: Renewable Storage when demand is **>160 kW** OR local hour is **18:00–22:00 inclusive**.
- Independent critical overload alert when demand is **>=200 kW**.
- Battery state-of-charge input and forecast/event history API.

## Local development

Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:9000.

Run the official evaluator from the repository root:

```bash
python test_eval.py
```

Generate the official prediction CSV format:

```bash
python predict.py --input sample_test_input.csv --output predictions.csv
```

Output columns are `timestamp,target_demand_kw`, preserving the input timestamp and returning one numeric prediction per row.

## QuickML training and publishing

1. Open the **HacksphereBITSHYD** project in Zoho Catalyst Console.
2. Open QuickML and upload the official `train_telemetry.csv` from the starter ZIP.
3. Train a regression model using `target_demand_kw` as the target. Use the timestamp and weather fields consistently with inference.
4. Evaluate the model, publish/deploy its endpoint, and check the endpoint's exact request and response schema.
5. Set `QUICKML_ENDPOINT_URL` in the runtime environment. The prediction adapter expects a POST body shaped as `{"data":[...]}` and a response containing `{"predictions":[...]}`.
6. The official starter endpoint template does not require an auth header; if your published endpoint has a different authentication or payload contract, adapt the request to the settings shown by Catalyst.

Until a published endpoint is configured, local predictions use the official starter-kit baseline and are labelled as demo fallback by the dashboard. They must not be represented as trained QuickML predictions.

## Zoho Catalyst AppSail deployment

Create a Python AppSail service inside the existing Catalyst project and deploy this repository.

- Install/build command: `pip install -r requirements.txt`
- Start command: `gunicorn --bind 0.0.0.0:$X_ZOHO_CATALYST_LISTEN_PORT app:app`
- Configure `QUICKML_ENDPOINT_URL` in AppSail environment variables.
- Never commit API tokens or credentials.
- Verify the app route and `/api/health` after deployment.

The included SQLite event log is a starter implementation. AppSail local filesystem persistence may be ephemeral; use Catalyst Data Store/NoSQL for durable production history and Stratus for uploaded-file storage as described in `PROBLEM_STATEMENT.md`.

## API routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/health` | Service and QuickML configuration status |
| GET | `/api/history` | Recent forecast event log |
| POST | `/api/forecast` | Validate 24 rows, predict, and apply dispatch rules |
| POST | `/api/telemetry` | Parse and validate a 24-row CSV upload |

## Environment variables

See `.env.example`. Set secrets only in Catalyst environment settings, never in source control.

## Deployment status

The GitHub application source is committed. QuickML model training/publishing and Catalyst AppSail deployment are separate authenticated steps that must be completed in the Catalyst project before a public live application URL can be claimed.
