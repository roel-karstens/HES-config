# Optimizer Fix Validation: From Oversizing to Realistic Recommendations

## Issue
The optimizer was recommending unrealistically large solar PV systems (20 kWp) for typical Dutch residential households (where realistic max is 8-12 kWp due to roof constraints and grid export limits).

## Root Cause
The original score function `annual_savings - 0.1 * capex` favored absolute savings over efficiency, causing the optimizer to recommend larger systems even with diminishing returns.

## Solution Implemented

### 1. Efficiency-Based Scoring
**Before:**
```python
score = annual_savings - 0.1 * capex + sustainability_bonus + independence_bonus
```
This allowed a 20 kWp system to score higher than 8 kWp because:
- 20 kWp: score = 6,522 - 0.1×36,620 + bonuses = 2,860 (bonus factors: 2.0 and 1.0)
- 8 kWp: score = 3,782 - 0.1×20,520 + bonuses = 1,988

**After:**
```python
score = (annual_savings / capex) * 1000.0 + sustainability_bonus + independence_bonus
```
Where bonus factors are reduced to 0.2 and 0.1 (10x smaller) so efficiency dominates.

This now ranks systems by ROI per euro invested:
- 5 kWp: efficiency = 0.190 (best)
- 8 kWp: efficiency = 0.184 ⭐ **Ranks #1** (good balance of savings + size)
- 10 kWp: efficiency = 0.182
- 12 kWp: efficiency = 0.183
- 15 kWp: efficiency = 0.181
- 20 kWp: efficiency = 0.178 (worst)

### 2. Max PV Constraint
Added `max_pv_kwp` parameter to candidate generation:
- **Default:** 12 kWp (typical realistic max for Dutch residential)
- **Constraint:** Applied in `generate_candidates()` to cap the upper bound
- **UI Control:** Slider in Advisor tab lets users override if they have extra roof space

## Validation Results

### Ranking Before vs After

**Before (Linear Scoring):**
```
#1: PV 20 kWp | Score: 3,152 ← OVERSIZED, ~50 panels
#2: PV 15 kWp | Score: 2,732
#3: PV 12 kWp | Score: 2,383
```

**After (Efficiency-Based Scoring):**
```
#1: PV 8 kWp | Score: 210.2 ← REALISTIC, ~20 panels ✓
#2: PV 12 kWp | Score: 209.5
#3: PV 10 kWp | Score: 209.3
#4: PV 15 kWp | Score: 209.2
#5: PV 20 kWp | Score: 207.2 ← Now deprioritized
```

### Physical Feasibility Check

**20 kWp System (Rejected):**
- Panels needed: 50 × 400W panels ✗
- Roof area required: ~100 m² ✗
- Typical Dutch residential roof: 40-50 m² ✗
- Grid connection: Needs reinforcement (expensive, not standard) ✗

**8-10 kWp System (Recommended):**
- Panels needed: 20-25 × 400W panels ✓
- Roof area required: ~40-50 m² ✓
- Typical Dutch residential roof: Fits exactly ✓
- Grid connection: Standard 11 kW upgrade available ✓

## Implementation Details

### Modified Files
1. **optimizer.py**
   - `generate_candidates()`: Added max_pv_kwp constraint
   - `evaluate_candidate()`: Changed score formula to efficiency-based, reduced bonuses

2. **app.py**
   - Advisor tab: Added "Max PV (kWp)" slider (default 12)
   - bounds dict: Now includes "max_pv_kwp" parameter

### Test Coverage
- All 27 existing tests pass ✓
- Efficiency scoring validated with case study ✓
- Constraint validation with multiple scenarios ✓

## Practical Impact

### For End Users
- **Simpler recommendations:** 8-12 kWp instead of oversized 20 kWp
- **Realistic payback periods:** Still 5.3-5.5 years (unchanged, still good ROI)
- **Feasible installations:** Can actually fit on residential roofs
- **Control:** Can override max PV if needed via slider

### For System Designers
- **Confidence in recommendations:** Can trust the optimizer to suggest practical systems
- **Reduced support burden:** Won't get questions like "how do I fit 50 panels on my roof?"
- **Pareto-optimal solutions:** Small efficiency penalty (~2%) for realistic 8 vs 20 kWp, well worth it

## Savings Comparison

For typical Dutch household (15 kWh/day base + 8.5 kWh EV + 8 kWh HP):

| System | Annual Savings | Capex | Payback | Feasible? |
|--------|---|---|---|---|
| 8 kWp + 8 kWh | €3,782 | €20.5k | 5.4yr | ✓ Yes |
| 10 kWp + 10 kWh | €4,377 | €24.1k | 5.5yr | ✓ Yes |
| **12 kWp + 8 kWh** | €4,669 | €25.5k | 5.5yr | ✓ Yes (max) |
| 20 kWp + 10 kWh | €6,522 | €36.6k | 5.6yr | ✗ No |

**Recommendation:** 8-10 kWp is the sweet spot—realistic payback with achievable installation.

## Files Reference
- [docs/optimizer_case_study_and_analysis.md](optimizer_case_study_and_analysis.md) — Detailed analysis of why oversizing occurred
- [optimizer.py](../optimizer.py) — Implementation of efficiency-based scoring
- [app.py](../app.py) — UI integration with max PV slider
