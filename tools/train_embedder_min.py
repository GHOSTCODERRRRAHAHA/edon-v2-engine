# add at the very top
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]  # repo root
sys.path.insert(0, str(ROOT))

from src.embedding import CAVEmbedder

import os, numpy as np, pandas as pd
from src.embedding import CAVEmbedder
rng = np.random.default_rng(42)
N = 5000  # small but enough to fit PCA/whitener
def sample(n):
    return pd.DataFrame({
        'hr'        : rng.normal(70, 10, n).clip(40, 180),
        'hrv_rmssd' : rng.normal(40, 15, n).clip(5, 200),
        'eda_mean'  : rng.uniform(0.05, 5.0, n),
        'eda_var'   : rng.uniform(0.001, 1.0, n),
        'resp_bpm'  : rng.normal(14, 3, n).clip(6, 30),
        'accel_mag' : rng.uniform(0.8, 2.0, n),
        'temp_c'    : rng.normal(22, 4, n).clip(10, 35),
        'humidity'  : rng.integers(10, 90, n),
        'cloud'     : rng.integers(0, 100, n),
        'aqi'       : rng.integers(10, 160, n),
        'pm25'      : rng.uniform(1, 80, n),
        'ozone'     : rng.uniform(10, 120, n),
        'hour'      : rng.integers(0, 24, n),
        'is_daylight': (rng.integers(0, 24, n) >= 7) & (rng.integers(0, 24, n) <= 19),
    }).astype({
        'humidity':'int64','cloud':'int64','aqi':'int64','hour':'int64','is_daylight':'int64'
    })
X = sample(N)
model_dir = os.environ.get("MODEL_DIR", "models")
emb = CAVEmbedder(n_components=128, model_dir=model_dir)
emb.fit(X)
emb.save()
print(f"Saved embedder to {model_dir}/")
