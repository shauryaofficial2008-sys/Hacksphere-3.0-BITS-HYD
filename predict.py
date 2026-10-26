"""HackSphere 3.0 evaluator contract + CLI. QuickML credentials are environment variables."""
import argparse, os
import numpy as np
import pandas as pd
import requests

QUICKML_ENDPOINT_URL = os.getenv("QUICKML_ENDPOINT_URL", "").strip()
QUICKML_API_TOKEN = os.getenv("QUICKML_API_TOKEN", "").strip()
FEATURES = ["timestamp", "ambient_temp_c", "humidity_pct", "solar_irradiance_wm2"]

def predict(input_df: pd.DataFrame):
    missing=[c for c in FEATURES if c not in input_df.columns]
    if missing: raise ValueError("Missing columns: "+", ".join(missing))
    frame=input_df[FEATURES].copy()
    frame["timestamp"]=pd.to_datetime(frame["timestamp"],errors="raise")
    for c in FEATURES[1:]: frame[c]=pd.to_numeric(frame[c],errors="raise")
    if frame.isna().any().any(): raise ValueError("Input contains missing values")
    if QUICKML_ENDPOINT_URL:
        headers={"Content-Type":"application/json"}
        if QUICKML_API_TOKEN: headers["Authorization"]="Zoho-oauthtoken "+QUICKML_API_TOKEN
        payload={"data":frame.assign(timestamp=frame.timestamp.dt.strftime("%Y-%m-%d %H:%M:%S")).to_dict(orient="records")}
        response=requests.post(QUICKML_ENDPOINT_URL,json=payload,headers=headers,timeout=30)
        response.raise_for_status()
        result=response.json()
        values=result.get("predictions",result.get("data"))
        if values is None: raise ValueError("QuickML response missing predictions")
        values=np.asarray(values,dtype=float).reshape(-1)
        if len(values)!=len(frame): raise ValueError("QuickML prediction count mismatch")
        if not np.isfinite(values).all(): raise ValueError("QuickML returned non-finite values")
        return values
    # Local contract fallback only; set QUICKML_ENDPOINT_URL for judged QuickML inference.
    h=frame.timestamp.dt.hour.to_numpy()
    temp=frame.ambient_temp_c.to_numpy()
    humidity=frame.humidity_pct.to_numpy()
    solar=frame.solar_irradiance_wm2.to_numpy()
    base=122+24*np.sin(2*np.pi*(h-7)/24)
    return np.maximum(35,base+np.maximum(temp-24,0)*5.2+np.maximum(humidity-65,0)*.10-np.minimum(solar,800)*.012)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",default="sample_test_input.csv")
    parser.add_argument("--output",default="predictions.csv")
    args=parser.parse_args()
    data=pd.read_csv(args.input)
    values=predict(data)
    out=pd.DataFrame({"timestamp":data["timestamp"],"target_demand_kw":values})
    out.to_csv(args.output,index=False)
    print(f"Wrote {len(out)} predictions to {args.output}")
if __name__=="__main__": main()
