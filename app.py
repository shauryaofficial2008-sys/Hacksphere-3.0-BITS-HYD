"""HackSphere 3.0 - Flask API and static dashboard for Zoho Catalyst AppSail."""
import csv, io, json, os, sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
DB_PATH = os.getenv("ENERGY_DB_PATH", str(ROOT / "energy_logs.db"))
app = Flask(__name__, static_folder="static")

FEATURES = ["timestamp", "ambient_temp_c", "humidity_pct", "solar_irradiance_wm2"]
QUICKML_URL = os.getenv("QUICKML_ENDPOINT_URL", "").strip()
QUICKML_TOKEN = os.getenv("QUICKML_API_TOKEN", "").strip()

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, event_type TEXT,
        payload TEXT NOT NULL)""")
    return conn

def log_event(kind, payload):
    try:
        with db() as conn:
            conn.execute("INSERT INTO events(created_at,event_type,payload) VALUES(?,?,?)",
                         (datetime.utcnow().isoformat()+"Z", kind, json.dumps(payload)))
    except Exception as exc:
        app.logger.warning("Could not persist event: %s", exc)

def validate_rows(rows):
    frame = pd.DataFrame(rows)
    missing = [c for c in FEATURES if c not in frame.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    frame = frame[FEATURES].copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    for col in FEATURES[1:]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    if frame.isna().any().any():
        raise ValueError("Input contains missing or invalid timestamps/weather values.")
    if ((frame["humidity_pct"] < 0) | (frame["humidity_pct"] > 100)).any():
        raise ValueError("humidity_pct must be between 0 and 100.")
    if (frame["solar_irradiance_wm2"] < 0).any():
        raise ValueError("solar_irradiance_wm2 cannot be negative.")
    return frame

def baseline_predict(frame):
    # Development-only fallback. Set QUICKML_ENDPOINT_URL for real model inference.
    hour = frame.timestamp.dt.hour.to_numpy()
    temp = frame.ambient_temp_c.to_numpy()
    solar = frame.solar_irradiance_wm2.to_numpy()
    humidity = frame.humidity_pct.to_numpy()
    daily = 122 + 24*np.sin(2*np.pi*(hour-7)/24)
    cooling = np.maximum(temp-24, 0)*5.2
    solar_relief = np.minimum(solar, 800)*0.012
    humidity_load = np.maximum(humidity-65, 0)*0.10
    return np.maximum(35, daily + cooling + humidity_load - solar_relief)

def quickml_predict(frame):
    if not QUICKML_URL:
        return baseline_predict(frame), "DEMO_FALLBACK"
    headers = {"Content-Type": "application/json"}
    if QUICKML_TOKEN:
        headers["Authorization"] = "Zoho-oauthtoken " + QUICKML_TOKEN
    response = requests.post(QUICKML_URL,
        json={"data": frame.assign(timestamp=frame.timestamp.dt.strftime("%Y-%m-%d %H:%M:%S")).to_dict(orient="records")},
        headers=headers, timeout=25)
    response.raise_for_status()
    result = response.json()
    values = result.get("predictions")
    if values is None and isinstance(result.get("data"), list):
        values = result["data"]
    if values is None:
        raise ValueError("QuickML response must contain a 'predictions' array.")
    values = np.asarray(values, dtype=float).reshape(-1)
    if len(values) != len(frame) or not np.isfinite(values).all():
        raise ValueError("QuickML returned invalid prediction count or values.")
    return values, "ZOHO_QUICKML"

def dispatch(demand, timestamp):
    hour = pd.Timestamp(timestamp).hour
    peak_window = 18 <= hour <= 22
    mode = "RENEWABLE_STORAGE" if demand > 160 or peak_window else "MAIN_GRID"
    critical = demand >= 200
    return {"grid_mode": mode, "alert": "CRITICAL_OVERLOAD" if critical else "NORMAL",
            "peak_window": peak_window, "dispatch_signal": "SWITCH_TO_BATTERY" if mode == "RENEWABLE_STORAGE" else "USE_MAIN_GRID"}

@app.get("/")
def index():
    return send_from_directory("static", "index.html")

@app.get("/api/health")
def health():
    return jsonify({"status":"ok","service":"hacksphere-energy-api","quickml_configured":bool(QUICKML_URL)})

@app.get("/api/history")
def history():
    try:
        with db() as conn:
            rows=conn.execute("SELECT created_at,event_type,payload FROM events ORDER BY id DESC LIMIT 30").fetchall()
        return jsonify([{"created_at":r[0],"event_type":r[1],"payload":json.loads(r[2])} for r in rows])
    except Exception as exc:
        return jsonify({"error":str(exc)}),500

@app.post("/api/forecast")
def forecast():
    try:
        body=request.get_json(silent=True) or {}
        rows=body.get("rows", [])
        if len(rows) != 24:
            return jsonify({"error":"Provide exactly 24 hourly feature rows."}),400
        frame=validate_rows(rows)
        predictions, source=quickml_predict(frame)
        output=[]
        for stamp, value in zip(frame.timestamp, predictions):
            value=round(float(value),2)
            state=dispatch(value,stamp)
            output.append({"timestamp":stamp.strftime("%Y-%m-%d %H:%M:%S"),
                           "target_demand_kw":value, **state})
        battery_soc=float(body.get("battery_soc",72))
        if not 0 <= battery_soc <= 100:
            return jsonify({"error":"battery_soc must be between 0 and 100."}),400
        summary={"average_kw":round(float(np.mean(predictions)),2),
                 "peak_kw":round(float(np.max(predictions)),2),
                 "peak_time":output[int(np.argmax(predictions))]["timestamp"],
                 "renewable_hours":sum(x["grid_mode"]=="RENEWABLE_STORAGE" for x in output),
                 "critical_hours":sum(x["alert"]=="CRITICAL_OVERLOAD" for x in output)}
        result={"predictions":output,"summary":summary,"model_source":source,
                "battery_soc":battery_soc,"generated_at":datetime.utcnow().isoformat()+"Z"}
        log_event("forecast",result)
        return jsonify(result)
    except requests.RequestException as exc:
        return jsonify({"error":"QuickML request failed: "+str(exc)}),502
    except (ValueError, TypeError) as exc:
        return jsonify({"error":str(exc)}),400
    except Exception as exc:
        app.logger.exception("Forecast failed")
        return jsonify({"error":"Forecast failed: "+str(exc)}),500

@app.post("/api/telemetry")
def telemetry():
    try:
        if "file" not in request.files:
            return jsonify({"error":"Upload a CSV file in the 'file' field."}),400
        raw=request.files["file"].read().decode("utf-8-sig")
        frame=pd.read_csv(io.StringIO(raw))
        frame=validate_rows(frame.to_dict(orient="records"))
        if len(frame) != 24:
            return jsonify({"error":"CSV must contain exactly 24 hourly rows."}),400
        rows=frame.assign(timestamp=frame.timestamp.dt.strftime("%Y-%m-%d %H:%M:%S")).to_dict(orient="records")
        return jsonify({"rows":rows,"count":len(rows)})
    except Exception as exc:
        return jsonify({"error":str(exc)}),400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT", os.getenv("PORT", "9000"))))
