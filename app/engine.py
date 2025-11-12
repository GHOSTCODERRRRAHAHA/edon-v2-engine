"""CAV Fusion Engine - Core computation logic."""

from pathlib import Path
from typing import Dict, Tuple, Optional

import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import welch
import warnings

warnings.filterwarnings("ignore")

# Configuration
ARTIFACTS_DIR = Path(__file__).parent.parent / "data" / "raw" / "wesad"
MODEL_FILE = ARTIFACTS_DIR / "model.pkl"
SCALER_FILE = ARTIFACTS_DIR / "scaler.pkl"
SCHEMA_FILE = ARTIFACTS_DIR / "feature_schema.json"

# Frequency bands for spectral features (Hz)
FREQ_BANDS = {
    "low": (0.04, 0.15),
    "mid": (0.15, 0.4),
    "high": (0.4, 1.0),
}
FS = 4  # Sampling rate in Hz
WINDOW_LEN = 240  # 60 seconds at 4 Hz
STRESS_LABEL = 2  # Stress label ID


def load_artifacts():
    """Load model, scaler, and feature schema using robust discovery."""
    # Always try robust loader first (v3.2 models)
    try:
        from app.engine_loader_patch import load_artifacts as load_artifacts_robust

        return load_artifacts_robust()
    except ImportError as e:
        # If import fails, check if file exists
        loader_path = Path(__file__).parent / "engine_loader_patch.py"
        if not loader_path.exists():
            raise ImportError(
                f"app/engine_loader_patch.py not found at {loader_path}. "
                f"Please ensure the file exists."
            ) from e

        # File exists but import failed - re-raise with more context
        raise ImportError(
            f"Could not import robust loader from {loader_path}: {e}. "
            f"Check for syntax errors or missing dependencies."
        ) from e
    except FileNotFoundError as e:
        # Robust loader found but artifacts missing - provide helpful error
        import os

        env_dir = os.getenv("EDON_MODEL_DIR", "not set")
        raise FileNotFoundError(
            f"Could not find v3.2 model artifacts. {str(e)}. "
            f"EDON_MODEL_DIR={env_dir}. "
            f"Ensure models are in one of: EDON_MODEL_DIR, ./models/, repo root, or cav_engine_v3_2_* folder."
        ) from e


def compute_basic_stats(signal: np.ndarray) -> Dict[str, float]:
    """Compute basic statistical features."""
    finite_mask = np.isfinite(signal)
    if np.sum(finite_mask) == 0:
        return {
            "mean": np.nan,
            "std": np.nan,
            "min": np.nan,
            "max": np.nan,
            "skew": np.nan,
            "kurtosis": np.nan,
        }

    signal_clean = signal[finite_mask]

    return {
        "mean": float(np.mean(signal_clean)),
        "std": float(np.std(signal_clean)),
        "min": float(np.min(signal_clean)),
        "max": float(np.max(signal_clean)),
        "skew": float(stats.skew(signal_clean, bias=False)),
        "kurtosis": float(stats.kurtosis(signal_clean, bias=False)),
    }


def compute_slope(signal: np.ndarray) -> float:
    """Compute slope from linear regression vs time."""
    finite_mask = np.isfinite(signal)
    if np.sum(finite_mask) < 2:
        return float("nan")

    signal_clean = signal[finite_mask]
    time = np.arange(len(signal_clean))

    slope, _ = np.polyfit(time, signal_clean, 1)
    return float(slope)


def compute_std_first_diff(signal: np.ndarray) -> float:
    """Compute standard deviation of first difference."""
    finite_mask = np.isfinite(signal)
    if np.sum(finite_mask) < 2:
        return float("nan")

    signal_clean = signal[finite_mask]
    diff = np.diff(signal_clean)

    return float(np.std(diff))


def compute_spectral_features(signal: np.ndarray, fs: float = 4.0) -> Dict[str, float]:
    """Compute spectral power features using Welch's method."""
    finite_mask = np.isfinite(signal)
    if np.sum(finite_mask) < 10:
        return {"power_low": np.nan, "power_mid": np.nan, "power_high": np.nan}

    signal_clean = signal[finite_mask]

    freqs, psd = welch(signal_clean, fs=fs, nperseg=min(len(signal_clean), 64))

    features = {}
    for band_name, (f_low, f_high) in FREQ_BANDS.items():
        band_mask = (freqs >= f_low) & (freqs <= f_high)
        power = np.trapz(psd[band_mask], freqs[band_mask])
        features[f"power_{band_name}"] = float(power)

    return features


def compute_eda_extras(signal: np.ndarray) -> Dict[str, float]:
    """Compute EDA-specific features: median and 95th percentile."""
    finite_mask = np.isfinite(signal)
    if np.sum(finite_mask) == 0:
        return {"median": np.nan, "p95": np.nan}

    signal_clean = signal[finite_mask]

    return {
        "median": float(np.median(signal_clean)),
        "p95": float(np.percentile(signal_clean, 95)),
    }


def compute_window_features(window_dict: Dict) -> pd.DataFrame:
    """Compute features for a single window."""
    features: Dict[str, float] = {}

    # Extract signals
    eda = np.asarray(window_dict.get("EDA", []), dtype=float)
    temp = np.asarray(window_dict.get("TEMP", []), dtype=float)
    bvp = np.asarray(window_dict.get("BVP", []), dtype=float)
    acc_x = np.asarray(window_dict.get("ACC_x", []), dtype=float)
    acc_y = np.asarray(window_dict.get("ACC_y", []), dtype=float)
    acc_z = np.asarray(window_dict.get("ACC_z", []), dtype=float)

    # Compute ACC magnitude
    if len(acc_x) > 0 and len(acc_y) > 0 and len(acc_z) > 0:
        acc_mag = np.sqrt(acc_x ** 2 + acc_y ** 2 + acc_z ** 2)
    else:
        acc_mag = np.array([], dtype=float)

    # Channels to process
    channels = {
        "EDA": eda,
        "TEMP": temp,
        "BVP": bvp,
        "ACC_mag": acc_mag,
    }

    # Extract features for each channel
    for channel_name, signal in channels.items():
        # Basic statistics
        basic_stats = compute_basic_stats(signal)
        for stat_name, stat_value in basic_stats.items():
            features[f"{channel_name}_{stat_name}"] = stat_value

        # Slope
        features[f"{channel_name}_slope"] = compute_slope(signal)

        # Std of first difference
        features[f"{channel_name}_std_diff"] = compute_std_first_diff(signal)

        # Spectral features for BVP and ACC_mag
        if channel_name in ["BVP", "ACC_mag"]:
            spectral = compute_spectral_features(signal, fs=FS)
            for spec_name, spec_value in spectral.items():
                features[f"{channel_name}_{spec_name}"] = spec_value

        # EDA extras
        if channel_name == "EDA":
            eda_extras = compute_eda_extras(signal)
            for extra_name, extra_value in eda_extras.items():
                features[f"{channel_name}_{extra_name}"] = extra_value

    # Create DataFrame
    df = pd.DataFrame([features])
    return df


def comfort_env(temp_c: float, humidity: float, aqi: int) -> float:
    """Compute environmental comfort score."""
    # Temperature comfort (20-24°C best)
    if 20 <= temp_c <= 24:
        temp_score = 1.0
    elif 18 <= temp_c < 20 or 24 < temp_c <= 26:
        temp_score = 0.8
    elif 16 <= temp_c < 18 or 26 < temp_c <= 28:
        temp_score = 0.6
    else:
        temp_score = 0.4

    # Humidity comfort (30-60% RH best)
    if 30 <= humidity <= 60:
        hum_score = 1.0
    elif 20 <= humidity < 30 or 60 < humidity <= 70:
        hum_score = 0.8
    elif 10 <= humidity < 20 or 70 < humidity <= 80:
        hum_score = 0.6
    else:
        hum_score = 0.4

    # AQI tiers
    if aqi <= 50:
        aqi_score = 1.0
    elif aqi <= 100:
        aqi_score = 0.8
    elif aqi <= 150:
        aqi_score = 0.6
    elif aqi <= 200:
        aqi_score = 0.4
    elif aqi <= 300:
        aqi_score = 0.2
    else:
        aqi_score = 0.1

    # Average of three factors
    env_comfort = (temp_score + hum_score + aqi_score) / 3.0

    return float(env_comfort)


def circadian_factor(local_hour: int) -> float:
    """Compute circadian factor based on local hour."""
    return 1.0 if 7 <= local_hour <= 21 else 0.7


class CAVEngine:
    """CAV Fusion Engine for computing context-aware scores."""

    def __init__(self, stress_label: int = 2, alpha: float = 0.2):
        """Initialize CAV engine."""
        self.stress_label = stress_label
        self.alpha = alpha
        self.model, self.scaler, self.schema = load_artifacts()
        self.feature_names = self.schema["feature_names"]

        # EMA state (per-instance, not global)
        self.cav_prev = None
        self.cav_smooth = None

        # Hysteresis state
        self._last_state = None

        # Weights (default) — make names consistent with 'parts'
        self.weights = {
            "bio": 0.6,
            "env": 0.2,
            "circadian": 0.2,  # was "circ"
        }

    def cav_from_window(
        self,
        window: Dict,
        temp_c: Optional[float] = None,
        humidity: Optional[float] = None,
        aqi: Optional[int] = None,
        local_hour: int = 12,
    ) -> Tuple[int, int, str, Dict]:
        """Compute CAV score from window and environmental data."""
        # Validate window length
        for key in ["EDA", "TEMP", "BVP", "ACC_x", "ACC_y", "ACC_z"]:
            if key not in window:
                parts = {"bio": 0.0, "env": 0.0, "circadian": 0.0, "p_stress": 0.0}
                return 0, 0, "overload", parts

            arr = np.asarray(window[key])
            if len(arr) != WINDOW_LEN:
                parts = {"bio": 0.0, "env": 0.0, "circadian": 0.0, "p_stress": 0.0}
                return 0, 0, "overload", parts

        # Check for missing values
        all_signals = np.concatenate(
            [
                np.asarray(window["EDA"]),
                np.asarray(window["TEMP"]),
                np.asarray(window["BVP"]),
                np.asarray(window["ACC_x"]),
                np.asarray(window["ACC_y"]),
                np.asarray(window["ACC_z"]),
            ]
        )

        if np.sum(~np.isfinite(all_signals)) > len(all_signals) * 0.2:  # >20% missing
            parts = {"bio": 0.0, "env": 0.0, "circadian": 0.0, "p_stress": 0.0}
            return 0, 0, "overload", parts

        # Compute features
        df_features = compute_window_features(window)

        # === DEBUG: check schema vs computed ===
        expected = list(self.feature_names)
        got = list(df_features.columns)

        missing = [c for c in expected if c not in got]
        unexpected = [c for c in got if c not in expected]
        overlap = [c for c in got if c in expected]
        ratio = (len(overlap) / max(1, len(expected)))

        print(
            f"[FEAT] expected={len(expected)} got={len(got)} "
            f"overlap={len(overlap)} ({ratio:.1%})",
            flush=True,
        )
        if missing[:10]:
            print("[FEAT] missing (first 10):", missing[:10], flush=True)
        if unexpected[:10]:
            print("[FEAT] unexpected (first 10):", unexpected[:10], flush=True)

        # Hard guard: avoid silently zero-filling a mismatched schema
        if ratio < 0.8:
            raise RuntimeError(
                f"Only {ratio:.1%} of expected features present; schema mismatch. "
                f"Missing={len(missing)} Unexpected={len(unexpected)}"
            )

        # Reindex to match training feature order (safe now)
        df_features = df_features.reindex(columns=self.feature_names, fill_value=0.0)

        # Standardize
        X_scaled = self.scaler.transform(df_features.values)
        X_scaled = np.nan_to_num(X_scaled, nan=0.0, posinf=0.0, neginf=0.0)

        # Predict
        if hasattr(self.model, "predict_proba"):
            proba = self.model.predict_proba(X_scaled)[0]

            # Handle XGBoost (0-indexed) vs sklearn (1-indexed)
            if hasattr(self.model, "classes_"):
                classes = self.model.classes_
                stress_idx = np.where(classes == self.stress_label)[0]
                if len(stress_idx) > 0:
                    stress_idx = stress_idx[0]
                else:
                    stress_idx = self.stress_label - 1
            else:
                stress_idx = self.stress_label - 1

            if stress_idx < 0 or stress_idx >= len(proba):
                stress_idx = 0

            p_stress = float(proba[stress_idx])
        else:
            pred = self.model.predict(X_scaled)[0]
            p_stress = 1.0 if pred == self.stress_label else 0.0

        # Bio score = 1 - P(stress)
        bio_score = 1.0 - p_stress

        # Environmental comfort
        if temp_c is not None and humidity is not None and aqi is not None:
            env_comfort = comfort_env(float(temp_c), float(humidity), int(aqi))
        else:
            env_comfort = 0.5  # Default neutral

        # Circadian factor
        circ_factor = circadian_factor(int(local_hour))

        # CAV = clip(weighted sum, 0..1) * 10000 → int
        cav_raw = (
            self.weights["bio"] * bio_score
            + self.weights["env"] * env_comfort
            + self.weights["circadian"] * circ_factor
        )
        cav_clipped = float(np.clip(cav_raw, 0.0, 1.0))
        cav_raw_int = int(cav_clipped * 10000)

        # EMA smoothing
        if self.cav_smooth is None:
            self.cav_smooth = cav_clipped
        else:
            self.cav_smooth = self.alpha * cav_clipped + (1 - self.alpha) * self.cav_smooth

        cav_smooth_int = int(self.cav_smooth * 10000)
        self.cav_prev = cav_raw_int

        # Get state from smoothed CAV
        state = self.state_from_cav(cav_smooth_int)

        parts = {
            "bio": float(bio_score),
            "env": float(env_comfort),
            "circadian": float(circ_factor),
            "p_stress": float(p_stress),
        }

        return cav_raw_int, cav_smooth_int, state, parts

    def state_from_cav(self, cav: int) -> str:
        """Determine state from CAV using hysteresis."""
        if self._last_state is None:
            if cav < 3000:
                state = "overload"
            elif cav < 7000:
                state = "balanced"
            elif cav < 9000:
                state = "focus"
            else:
                state = "restorative"
        else:
            if self._last_state == "overload":
                if cav >= 3300:
                    if cav < 7000:
                        state = "balanced"
                    elif cav < 9000:
                        state = "focus"
                    else:
                        state = "restorative"
                else:
                    state = "overload"
            elif self._last_state == "balanced":
                if cav < 2700:
                    state = "overload"
                elif cav >= 7300:
                    if cav < 9000:
                        state = "focus"
                    else:
                        state = "restorative"
                else:
                    state = "balanced"
            elif self._last_state == "focus":
                if cav < 6700:
                    if cav < 3000:
                        state = "overload"
                    else:
                        state = "balanced"
                elif cav >= 9300:
                    state = "restorative"
                else:
                    state = "focus"
            else:  # restorative
                if cav < 8700:
                    if cav < 7000:
                        if cav < 3000:
                            state = "overload"
                        else:
                            state = "balanced"
                    else:
                        state = "focus"
                else:
                    state = "restorative"

        self._last_state = state
        return state
