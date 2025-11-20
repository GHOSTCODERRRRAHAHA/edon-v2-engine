# EDON v1.1.0 - State Classification Enhancement

**Date**: 2025-11-20  
**Version**: v1.1.0

---

## 🎯 Changes

### Enhanced State Classification

Updated `classify_state()` function in `app/engine.py` to include a more nuanced "focus" state that requires environmental and circadian alignment.

**New State Mapping Logic**:

1. **overload**: `p_stress ≥ 0.8` - High stress always triggers overload
2. **restorative**: `p_stress < 0.2` - Very low stress, optimal recovery
3. **focus**: `0.2 ≤ p_stress ≤ 0.5` AND `env ≥ 0.8` AND `circadian ≥ 0.9` - Moderate stress with strong alignment
4. **balanced**: `0.2 ≤ p_stress < 0.8` (when focus conditions not met) - Normal operation

**Key Improvements**:
- "Focus" state now requires excellent environment (`env ≥ 0.8`) and circadian alignment (`circadian ≥ 0.9`)
- This makes "focus" more meaningful for demos and investors - it indicates optimal conditions for performance
- Preserves continuous scores so OEMs can still build richer logic
- Keeps overload behavior identical (high stress always triggers overload)

---

## 📝 Files Modified

1. **`app/engine.py`**
   - Updated `classify_state()` function with new logic
   - Added detailed docstring explaining state mapping

2. **`docs/OEM_API_CONTRACT.md`**
   - Updated "State Values" section with new conditions
   - Added state mapping logic explanation

3. **`docs/OEM_INTEGRATION.md`**
   - Updated "State Classification" section
   - Added reference to MODEL_CARD.md

4. **`README.md`**
   - Updated version to v1.1.0
   - Added state classification section with new logic
   - Added reference to MODEL_CARD.md

5. **`VERSION`**
   - Updated to `1.1.0`

6. **`MODEL_CARD.md`** (NEW)
   - Created comprehensive model card
   - Documents state mapping logic in detail
   - Includes version history

---

## 🔄 Migration Notes

### For OEMs

**No breaking changes** - The API contract remains the same. The state values are still:
- `restorative`
- `balanced`
- `focus`
- `overload`

**What Changed**:
- The conditions for "focus" state are now more strict
- Some windows that were previously "balanced" may now be "focus" (if conditions are met)
- Some windows that were previously "focus" may now be "balanced" (if conditions aren't met)

**Impact**:
- Minimal - most state classifications remain the same
- "Focus" state will be less common but more meaningful
- OEMs can still use continuous scores (`p_stress`, `env`, `circadian`) for custom logic

---

## 📊 Expected Behavior

### Before (v1.0.1)
- `p_stress` 0.2-0.5 → "balanced"
- `p_stress` 0.5-0.8 → "focus"
- `p_stress` < 0.2 → "restorative"
- `p_stress` ≥ 0.8 → "overload"

### After (v1.1.0)
- `p_stress` < 0.2 → "restorative"
- `p_stress` 0.2-0.5 AND `env ≥ 0.8` AND `circadian ≥ 0.9` → "focus"
- `p_stress` 0.2-0.8 (when focus conditions not met) → "balanced"
- `p_stress` ≥ 0.8 → "overload"

---

## ✅ Testing Recommendations

1. **Test with demo scenarios**:
   - Verify "focus" state appears when conditions are met
   - Verify "balanced" state when conditions aren't met

2. **Validate state transitions**:
   - Test transitions between states
   - Verify overload behavior unchanged

3. **Check OEM integrations**:
   - Ensure existing integrations still work
   - Verify state-based control logic behaves as expected

---

## 📚 Documentation Updates

- ✅ `MODEL_CARD.md` - New comprehensive model card
- ✅ `docs/OEM_API_CONTRACT.md` - Updated state values
- ✅ `docs/OEM_INTEGRATION.md` - Updated state classification
- ✅ `README.md` - Added state mapping explanation

---

**Status**: ✅ Complete  
**Version**: v1.1.0  
**Breaking Changes**: None

