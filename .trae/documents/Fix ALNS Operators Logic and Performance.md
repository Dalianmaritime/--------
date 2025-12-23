# ALNS Operators Fix and Optimization Plan

The AI's feedback is highly valid and critical. The current implementation has flawed objective functions in operators and significant performance bottlenecks.

## 1. Objective Function Mismatch Fix
*   **Issue**: `greedy_insertion` and `worst_removal` only consider distance (`dist_cost`), ignoring loading rate (`load_rate`) and the weights (`ALPHA`, `BETA`).
*   **Fix**:
    *   Import `Config` in `alns_operators.py`.
    *   Implement a helper method `_calculate_weighted_cost(route)` that returns `Config.ALPHA * (1 - route.load_rate) + Config.BETA * route.dist_cost`.
    *   Update `greedy_insertion`, `worst_removal`, and `regret_2_insertion` to use this weighted cost instead of raw distance.

## 2. Regret Operator Fix
*   **Issue**: `new_route_cost` is estimated as `dist * 2`, ignoring the huge penalty for low load rate (high `ALPHA`).
*   **Fix**:
    *   When evaluating a potential new route for a node, create a temporary `Route` object (or use `fleet_mgr` to generate one).
    *   Calculate its weighted cost using the same formula as above. This will naturally include the penalty for a single-item truck (low load rate).

## 3. Shaw Removal Normalization Fix
*   **Issue**: `dist + 0.00001 * vol_diff` uses a magic number that fails when units differ (e.g., mm vs mm³).
*   **Fix**:
    *   Normalize distance and volume differences by dividing by the max distance and max volume difference in the current solution (or fleet).
    *   Formula: `R = (dist_ij / max_dist) + (vol_diff_ij / max_vol_diff)`.

## 4. Performance Optimization
*   **Issue 1**: `_rebuild_solution` recalculates *all* routes, even unchanged ones.
*   **Fix 1**:
    *   In `_rebuild_solution`, identify which routes were actually modified (i.e., contained removed nodes).
    *   Only call `fleet_mgr.find_best_vehicle` for modified routes. Keep unchanged routes as is.
*   **Issue 2**: `_find_all_insertion_costs` runs 3D packing for every possibility.
*   **Fix 2**:
    *   In `_find_all_insertion_costs`, add a 1D check (Volume/Weight) *before* calling `fleet_mgr.find_best_vehicle` (note: `fleet_mgr` might already have this, but we should ensure it's efficient or add a pre-check here to avoid the method call overhead if possible, or rely on `fleet_mgr`'s internal 1D check if it's fast enough).
    *   Actually, `fleet_mgr.find_best_vehicle` does 1D check. To optimize further, we can check if `current_load + node_weight > max_vehicle_capacity` before even calling `fleet_mgr`.

## Execution Steps
1.  **Modify `alns_operators.py`**:
    *   Add `from config import Config`.
    *   Add `_calculate_weighted_cost` helper.
    *   Refactor `greedy_insertion` to use weighted cost.
    *   Refactor `worst_removal` to use weighted cost.
    *   Refactor `regret_2_insertion` to correctly calculate new route cost with load rate penalty.
    *   Refactor `shaw_removal` to use normalized metrics.
    *   Optimize `_rebuild_solution` to only re-evaluate modified routes.
    *   Add 1D capacity pre-checks in insertion loops.

2.  **Verify**:
    *   Run `test_runner.py` (or `main.py` with the small instance) to ensure logic holds and performance improves.
