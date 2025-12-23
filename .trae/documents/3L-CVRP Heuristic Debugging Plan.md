# 3L-CVRP Algorithm Debugging and Verification Plan

Based on the code structure and `idea.md` analysis, I have identified missing components (e.g., `_calc_load_rate` is empty) and potential logic gaps. I will proceed with the following steps:

## Phase 1: Code Completion & Integrity Check
1.  **Implement Missing Logic**:
    *   `packer_3d.py`: Complete the `_calc_load_rate` function (currently `pass`).
    *   `geometry_kernel.py`: Investigate and fix the `return False` placeholder at line 51 to ensure `check_support` works correctly.
    *   `alns_solver.py`: Verify existence of helper methods (`_roulette_select`, `_update_score`) which appeared missing in the preview.
2.  **Constraint Verification**:
    *   Double-check `alns_operators.py` to ensure the **Bonded Warehouse (保税仓)** constraint strictly enforces "first visit after depot".

## Phase 2: Test Environment Setup
1.  **Create Synthetic Data**:
    *   Since I cannot parse the PDF directly, I will create a `test_runner.py` with a **small hardcoded instance**:
        *   **Nodes**: 1 Depot + 5 Customers (including 1 Bonded Warehouse).
        *   **Items**: ~10 items with varying dimensions ($l, w, h$).
        *   **Fleet**: 2 Vehicle types (Small & Large) to test dynamic fleet selection.
2.  **Pipeline Integration**:
    *   Link `Data Model` -> `ALNS Solver` -> `Packer` -> `Output`.

## Phase 3: Iterative Execution & Debugging
1.  **Runtime Debugging**:
    *   Run `test_runner.py`.
    *   Fix immediate Python errors (Imports, TypeErrors, AttributeErrors).
2.  **Logic Debugging**:
    *   Verify **3D Packing**: Ensure items don't overlap and fit within vehicle boundaries.
    *   Verify **Sequence Dependency**: Ensure items for later stops are not blocking earlier stops (LIFO).
3.  **Performance Check**: Ensure the ALNS loop converges and produces a valid route.

## Phase 4: Final Validation & Reporting
1.  **Output Generation**:
    *   Print the Final Solution: Routes, Vehicle Types, Total Cost, Load Rates.
    *   Confirm all constraints (Bonded, Sequence, Support) are met.
