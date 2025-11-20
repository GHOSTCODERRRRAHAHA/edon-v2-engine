# EDON CAV Engine Model Card

**Version**: v1.1.0  
**Date**: 2025-11-20

---

## Model Overview

**Model Name**: `cav_state_v3_2`  
**Algorithm**: LightGBM (Gradient Boosting)  
**Purpose**: Context-Aware Vector (CAV) computation for adaptive state classification

---

## Training Data

- **Dataset**: WESAD (Wearable Stress and Affect Detection)
- **Training Windows**: 100,000 windows
- **Window Length**: 240 samples (4 seconds @ 60Hz, or equivalent)
- **Features**: 6 physiological + environmental features

---

## Input Features

### Physiological Features (6)
1. `eda_mean` - Electrodermal activity mean
2. `eda_std` - Electrodermal activity standard deviation
3. `bvp_mean` - Blood volume pulse mean
4. `bvp_std` - Blood volume pulse standard deviation
5. `acc_mean` - Accelerometer magnitude mean
6. `acc_std` - Accelerometer magnitude standard deviation

### Environmental Context
- `temp_c` - Ambient temperature (°C)
- `humidity` - Relative humidity (%)
- `aqi` - Air Quality Index
- `local_hour` - Local hour [0-23]

---

## Output

### CAV Scores
- **cav_raw**: Raw CAV score [0-10000]
- **cav_smooth**: EMA-smoothed CAV score [0-10000]

### Component Scores
- **bio**: Biological score [0.0-1.0]
- **env**: Environmental comfort score [0.0-1.0]
- **circadian**: Circadian alignment score [0.0-1.0]
- **p_stress**: Probability of stress [0.0-1.0]

### State Classification

EDON classifies into one of four states based on `p_stress`, `env`, and `circadian` scores:

| State | Conditions | Description |
|-------|------------|-------------|
| **restorative** | `p_stress < 0.2` | Very low stress, optimal recovery state |
| **focus** | `0.2 ≤ p_stress ≤ 0.5` AND `env ≥ 0.8` AND `circadian ≥ 0.9` | Moderate stress with strong environmental and circadian alignment - indicates focused, productive state |
| **balanced** | `0.2 ≤ p_stress < 0.8` (when focus conditions not met) | Normal operation with moderate stress levels |
| **overload** | `p_stress ≥ 0.8` | High stress requiring intervention, regardless of other factors |

**State Mapping Logic**:
1. **Overload** is checked first - high stress always triggers overload
2. **Restorative** is for very low stress (< 0.2)
3. **Focus** requires moderate stress (0.2-0.5) combined with excellent environment (≥ 0.8) and circadian alignment (≥ 0.9)
4. **Balanced** is the default for moderate stress when focus conditions aren't met

---

## Performance Characteristics

- **Throughput**: 50-100 windows/sec (single CPU core)
- **Latency**: 10-20ms median (p50), 30-50ms p99
- **Accuracy**: Model trained on WESAD dataset with stress detection focus

---

## Limitations

- Model trained on synthetic + WESAD-style data
- OEMs should validate on their own sensor stack
- State thresholds may need tuning for specific use cases
- Environmental and circadian scores influence "focus" state classification

---

## Version History

- **v1.1.0** (2025-11-20): Enhanced state classification with "focus" state requiring environmental and circadian alignment
- **v1.0.1** (2025-11-20): Initial production release
- **v1.0.0** (2025-11-20): First stable release

---

## References

- WESAD Dataset: https://ieeexplore.ieee.org/document/8589068
- LightGBM: https://lightgbm.readthedocs.io/

