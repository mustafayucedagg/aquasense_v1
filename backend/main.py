import os
import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
from collections import deque
from typing import Optional
from datetime import datetime

import ai
import database
import reports

MODEL_PATH = os.path.join(os.path.dirname(__file__), "aquasense_model_v2_g7.pkl")

PRESSURE_NODES = [f"P_Node_{i}" for i in range(2, 33)]
FLOW_LINKS     = [f"F_Link_{i}" for i in range(1, 35)]
DEMAND_NODES   = [f"D_Node_{i}" for i in range(1, 33)]

model = None
pressure_buffer = {col: deque([0.0, 0.0, 0.0], maxlen=3) for col in PRESSURE_NODES}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    if not os.path.exists(MODEL_PATH):
        raise RuntimeError(f"Model bulunamadı: {MODEL_PATH}")
    model = joblib.load(MODEL_PATH)
    print(f"Model yüklendi: {MODEL_PATH}")
    database.init_db()
    yield

app = FastAPI(title="AquaSense API", version="2.0", lifespan=lifespan)
app.include_router(database.router)
app.include_router(ai.router)
app.include_router(reports.router)

class SensorReading(BaseModel):
    P_Node_2: float;  P_Node_3: float;  P_Node_4: float;  P_Node_5: float
    P_Node_6: float;  P_Node_7: float;  P_Node_8: float;  P_Node_9: float
    P_Node_10: float; P_Node_11: float; P_Node_12: float; P_Node_13: float
    P_Node_14: float; P_Node_15: float; P_Node_16: float; P_Node_17: float
    P_Node_18: float; P_Node_19: float; P_Node_20: float; P_Node_21: float
    P_Node_22: float; P_Node_23: float; P_Node_24: float; P_Node_25: float
    P_Node_26: float; P_Node_27: float; P_Node_28: float; P_Node_29: float
    P_Node_30: float; P_Node_31: float; P_Node_32: float
    F_Link_1: float;  F_Link_2: float;  F_Link_3: float;  F_Link_4: float
    F_Link_5: float;  F_Link_6: float;  F_Link_7: float;  F_Link_8: float
    F_Link_9: float;  F_Link_10: float; F_Link_11: float; F_Link_12: float
    F_Link_13: float; F_Link_14: float; F_Link_15: float; F_Link_16: float
    F_Link_17: float; F_Link_18: float; F_Link_19: float; F_Link_20: float
    F_Link_21: float; F_Link_22: float; F_Link_23: float; F_Link_24: float
    F_Link_25: float; F_Link_26: float; F_Link_27: float; F_Link_28: float
    F_Link_29: float; F_Link_30: float; F_Link_31: float; F_Link_32: float
    F_Link_33: float; F_Link_34: float
    D_Node_1: float;  D_Node_2: float;  D_Node_3: float;  D_Node_4: float
    D_Node_5: float;  D_Node_6: float;  D_Node_7: float;  D_Node_8: float
    D_Node_9: float;  D_Node_10: float; D_Node_11: float; D_Node_12: float
    D_Node_13: float; D_Node_14: float; D_Node_15: float; D_Node_16: float
    D_Node_17: float; D_Node_18: float; D_Node_19: float; D_Node_20: float
    D_Node_21: float; D_Node_22: float; D_Node_23: float; D_Node_24: float
    D_Node_25: float; D_Node_26: float; D_Node_27: float; D_Node_28: float
    D_Node_29: float; D_Node_30: float; D_Node_31: float; D_Node_32: float
    hour: int
    timestamp: Optional[str] = None

def build_feature_vector(reading: SensorReading) -> np.ndarray:
    raw = reading.model_dump()
    pressure_vals = {col: raw[col] for col in PRESSURE_NODES}
    flow_vals     = [raw[col] for col in FLOW_LINKS]
    demand_vals   = [raw[col] for col in DEMAND_NODES]
    hour          = raw["hour"]
    is_night      = 1 if 2 <= hour <= 4 else 0
    roll3_vals, diff1_vals = [], []
    for col in PRESSURE_NODES:
        buf = pressure_buffer[col]
        prev = buf[-1]
        buf.append(pressure_vals[col])
        roll3_vals.append(float(np.mean(buf)))
        diff1_vals.append(pressure_vals[col] - prev)
    feature_vector = (
        list(pressure_vals.values()) + flow_vals + demand_vals +
        [hour, is_night] + roll3_vals + diff1_vals
    )
    return np.array(feature_vector, dtype=np.float32).reshape(1, -1)

def get_suspicious_nodes(reading: SensorReading, top_n: int = 3) -> list:
    raw = reading.model_dump()
    scores = model.get_booster().get_score(importance_type="gain")
    node_scores = {}
    for col in PRESSURE_NODES:
        importance = scores.get(col, 0.0)
        buf_mean = float(np.mean(pressure_buffer[col]))
        deviation = abs(raw[col] - buf_mean)
        node_scores[col] = importance * deviation
    top_nodes = sorted(node_scores, key=node_scores.get, reverse=True)[:top_n]
    return [n.replace("P_", "") for n in top_nodes]

@app.get("/")
def root():
    return {"status": "ok", "service": "AquaSense API v2"}

@app.get("/health")
def health():
    return {"model_loaded": model is not None}

@app.post("/predict")
def predict(reading: SensorReading):
    if model is None:
        raise HTTPException(status_code=503, detail="Model henüz yüklenmedi.")
    X = build_feature_vector(reading)
    proba = float(model.predict_proba(X)[0][1])
    prediction = int(proba >= 0.5)
    suspicious = get_suspicious_nodes(reading) if prediction == 1 else []
    return {
        "prediction": prediction,
        "leak_probability": round(proba, 4),
        "suspicious_nodes": suspicious,
        "timestamp": reading.timestamp or datetime.now().isoformat(),
    }

@app.post("/reset_buffer")
def reset_buffer():
    global pressure_buffer
    pressure_buffer = {col: deque([0.0, 0.0, 0.0], maxlen=3) for col in PRESSURE_NODES}
    return {"status": "buffer sıfırlandı"}