"""CAV embedding generation using PCA + (optional) random projection to 128-D."""

import os
import json
import joblib
import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from sklearn.preprocessing import StandardScaler, Normalizer
from sklearn.decomposition import PCA
from sklearn.random_projection import GaussianRandomProjection


FEATURE_COLS = [
    "hr", "hrv_rmssd", "eda_mean", "eda_var", "resp_bpm", "accel_mag",
    "temp_c", "humidity", "cloud", "aqi", "pm25", "ozone", "hour", "is_daylight",
]


class CAVEmbedder:
    """Generate 128-dimensional CAV embeddings from features."""

    def __init__(self, n_components: int = 128, model_dir: str = "models"):
        self.n_components = n_components
        self.model_dir = model_dir

        self.scaler = StandardScaler(with_mean=True, with_std=True)
        self.pca: Optional[PCA] = None
        self.rproj: Optional[GaussianRandomProjection] = None
        self.post_normalizer = Normalizer(norm="l2")

        self.feature_order: Optional[List[str]] = None
        self.is_fitted = False

        os.makedirs(model_dir, exist_ok=True)

    # ------------------------
    # utils
    # ------------------------
    def _model_path(self):
        return os.path.join(self.model_dir, "cav_embedder.joblib")

    def _legacy_paths(self):
        return (
            os.path.join(self.model_dir, "scaler.joblib"),
            os.path.join(self.model_dir, "pca.joblib"),
            os.path.join(self.model_dir, "rproj.joblib"),
            os.path.join(self.model_dir, "feature_order.json"),
        )

    def _select_and_order(self, df: pd.DataFrame) -> pd.DataFrame:
        """Reindex to the stored feature order; fill missing with 0.0."""
        if self.feature_order is None:
            # first-time fit path uses intersection order
            cols = [c for c in FEATURE_COLS if c in df.columns]
            return df[cols]
        # transform path: enforce exact order, fill missing
        return df.reindex(columns=self.feature_order, fill_value=0.0)

    # ------------------------
    # API
    # ------------------------
    def fit(self, features_df: pd.DataFrame) -> None:
        """Fit scaler, PCA (<= #features), and optional random projection to target dims."""
        X_df = self._select_and_order(features_df)
        if X_df.shape[1] == 0:
            raise ValueError("No valid feature columns found")

        # remember the exact column order used during fit
        self.feature_order = list(X_df.columns)

        X = X_df.values
        X_scaled = self.scaler.fit_transform(X)

        # PCA cannot exceed n_features
        pca_dim = min(self.n_components, X_scaled.shape[1])
        self.pca = PCA(n_components=pca_dim, svd_solver="auto", random_state=42)
        X_pca = self.pca.fit_transform(X_scaled)

        # normalize before the (possible) random projection
        X_pca = self.post_normalizer.fit_transform(X_pca)

        if self.n_components > pca_dim:
            # up-project to 128 with a stable random projection
            self.rproj = GaussianRandomProjection(
                n_components=self.n_components, random_state=42
            )
            X_embed = self.rproj.fit_transform(X_pca)
        else:
            self.rproj = None
            X_embed = X_pca

        # final normalizer fit at target space
        _ = self.post_normalizer.fit(X_embed)

        self.is_fitted = True
        self.save()

    def transform(self, features_df: pd.DataFrame) -> np.ndarray:
        """Transform features to n_components-D embeddings (default 128)."""
        if not self.is_fitted or self.pca is None:
            raise ValueError("Embedder must be fitted (load() or fit()) before transform")

        X_df = self._select_and_order(features_df)
        X_scaled = self.scaler.transform(X_df.values)

        X_pca = self.pca.transform(X_scaled)
        X_pca = self.post_normalizer.transform(X_pca)

        if self.rproj is not None:
            X_embed = self.rproj.transform(X_pca)
        else:
            X_embed = X_pca

        X_embed = self.post_normalizer.transform(X_embed)
        return X_embed

    def fit_transform(self, features_df: pd.DataFrame) -> np.ndarray:
        self.fit(features_df)
        return self.transform(features_df)

    def save(self) -> None:
        """Save everything in a single joblib (preferred)."""
        obj = {
            "n_components": self.n_components,
            "scaler": self.scaler,
            "pca": self.pca,
            "rproj": self.rproj,
            "post_normalizer": self.post_normalizer,
            "feature_order": self.feature_order,
            "is_fitted": self.is_fitted,
        }
        joblib.dump(obj, self._model_path())

    def load(self) -> None:
        """Load from single file, or fall back to legacy separate files if present."""
        path = self._model_path()
        if os.path.exists(path):
            obj = joblib.load(path)
            self.n_components = obj["n_components"]
            self.scaler = obj["scaler"]
            self.pca = obj["pca"]
            self.rproj = obj["rproj"]
            self.post_normalizer = obj["post_normalizer"]
            self.feature_order = obj["feature_order"]
            self.is_fitted = bool(obj.get("is_fitted", True))
            return

        # legacy fallback
        scaler_p, pca_p, rproj_p, feat_p = self._legacy_paths()
        if os.path.exists(scaler_p) and os.path.exists(pca_p):
            self.scaler = joblib.load(scaler_p)
            self.pca = joblib.load(pca_p)
            self.rproj = joblib.load(rproj_p) if os.path.exists(rproj_p) else None
            if os.path.exists(feat_p):
                with open(feat_p, "r") as f:
                    self.feature_order = json.load(f)
            else:
                self.feature_order = FEATURE_COLS  # best effort
            self.is_fitted = True
            # also write the unified file for next time
            self.save()
            return

        raise FileNotFoundError(
            f"Model files not found in {self.model_dir}. Train first."
        )


def generate_cav_from_features(features: Dict) -> List[float]:
    """(Unused helper) Prefer using CAVEmbedder directly."""
    raise NotImplementedError("Use CAVEmbedder.fit/transform")


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    v1 = np.asarray(vec1, dtype=float)
    v2 = np.asarray(vec2, dtype=float)
    if v1.shape != v2.shape:
        raise ValueError("Vectors must have same shape")
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 == 0 or n2 == 0:
        return 0.0
    return float(np.dot(v1, v2) / (n1 * n2))
