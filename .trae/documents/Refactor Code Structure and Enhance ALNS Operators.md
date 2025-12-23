# Refactoring and ALNS Operator Enhancement Plan

I will refactor the codebase to follow a clean structural pattern and implement advanced ALNS operators tailored to the 3L-CVRP with Bonded Warehouse constraints.

## 1. Structural Refactoring
*   **Target**: `d:\Learning_In_TsingHua\Homework\高级运筹学\【启发式】大作业\data_model.py`
*   **Action**: Move the `Solution` class from `test_runner.py` to `data_model.py`. This ensures `Solution`, `Route`, `Node`, and `Item` are all in the data layer.

## 2. Advanced ALNS Operators Design (`alns_operators.py`)
I will completely rewrite `alns_operators.py` to include a rich set of operators designed for this specific problem.

### Destroy Operators (Removing Nodes)
1.  **`random_removal`**: Randomly removes $N$ nodes to diversify the search.
2.  **`worst_removal`**: Removes nodes that contribute the most to the route cost (high detour distance). This helps prune inefficient route segments.
3.  **`shaw_removal` (Relatedness Removal)**: Removes a set of "related" nodes.
    *   **Design**: Relatedness will be defined by **Distance** (spatial proximity) and **Volume** (demand similarity).
    *   **Goal**: Removing clustered or similar nodes together allows the Repair operators to restructure that specific region more effectively.

### Repair Operators (Re-inserting Nodes)
1.  **`greedy_insertion`**: Inserts nodes into the position with the lowest cost increase.
    *   **Constraint Handling**: Will strictly enforce that Bonded Warehouses can *only* be inserted at Index 1 (immediately after Depot).
2.  **`regret_2_insertion`**: Calculates the "regret" value (difference between best and 2nd best insertion cost).
    *   **Goal**: Prioritizes "difficult" nodes (e.g., large items or Bonded nodes) that would be very expensive if not inserted in their optimal position. This is critical for minimizing the number of trucks.

## 3. Integration and Verification
*   **Update `alns_solver.py`**: Ensure the solver correctly initializes and uses these new operators.
*   **Update `test_runner.py`**:
    *   Remove temporary classes.
    *   Register the full list of Destroy/Repair operators.
    *   Run the full simulation to verify the enhanced algorithm performs well and respects all constraints.

## Execution Steps
1.  **Modify `data_model.py`**: Add `Solution` class.
2.  **Modify `alns_operators.py`**: Implement the class with `random_removal`, `worst_removal`, `shaw_removal`, `greedy_insertion`, and `regret_2_insertion`.
3.  **Modify `test_runner.py`**: Clean up and link everything.
4.  **Run & Debug**: Execute `test_runner.py` to prove "Full Health" execution.
