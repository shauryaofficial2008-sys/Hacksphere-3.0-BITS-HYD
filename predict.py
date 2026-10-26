"""HackSphere 3.0 official inference contract.

Set QUICKML_ENDPOINT_URL to the published Catalyst QuickML endpoint before
submission. The fallback intentionally mirrors the official starter kit so
that the evaluator can validate the predict(input_df) contract locally.
"""
import os
import numpy as np
import pandas as pd
import requests

QUICKML_ENDPOINT_URL = os.getenv("QUICKML_ENDPOINT_URL", "").strip()

def predict(input_df: pd.DataFrame):
    """Return one predicted demand value (kW) for each input row."""
    required = ["timestamp", "ambient_temp_c", "humidity_pct", "solar_irradiance_wm2"]
    missing = [column for column in required if column not in input_df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    frame = input_df[required].copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    for column in required[1:]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame.isna().any().any():
        raise ValueError("Input contains missing or invalid telemetry values.")

    if QUICKML_ENDPOINT_URL and QUICKML_ENDPOINT_URL != "YOUR_PUBLISHED_QUICKML_ENDPOINT_URL_HERE":
        try:
            payload = {"data": input_df.to_dict(orient="records")}
            response = requests.post(QUICKML_ENDPOINT_URL, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            predictions = np.asarray(result["predictions"], dtype=float).reshape(-1)
            if len(predictions) != len(frame) or not np.isfinite(predictions).all():
                raise ValueError("QuickML returned an invalid prediction array.")
            return predictions
        except Exception as exc:
            print(f"Warning: QuickML endpoint call failed ({exc}). Falling back to starter baseline.")

    hours = frame["timestamp"].dt.hour
    base_load = 120.0 + 30.0 * np.sin(2 * np.pi * (hours - 6) / 24)
    cooling_load = np.maximum(0.0, frame["ambient_temp_c"] - 24.0) * 8.5
    return np.asarray((base_load + cooling_load).values, dtype=float)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="sample_test_input.csv")
    parser.add_argument("--output", default="predictions.csv")
    args = parser.parse_args()
    sample_df = pd.read_csv(args.input)
    predictions = predict(sample_df)
    pd.DataFrame({"timestamp": sample_df["timestamp"], "target_demand_kw": predictions}).to_csv(args.output, index=False)
    print(f"Generated {len(predictions)} predictions -> {args.output}")
