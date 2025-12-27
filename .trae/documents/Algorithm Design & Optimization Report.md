# Summary Report Generation

## 1. Algorithm Overview
- **Core Framework**: Adaptive Large Neighborhood Search (ALNS) integrated with Simulated Annealing (SA).
- **Optimization Goal**: Minimize a weighted sum of transport costs (distance) and maximize vehicle utilization (volume/weight).
- **Search Strategy**: Dynamically selects Destroy (removal) and Repair (insertion) operators based on their historical performance to escape local optima.

## 2. 3D Packing Logic (Sequence-Dependent Extreme Point Heuristic)
- **Heuristic**: Extreme Point (EP) based placement.
- **Sequence Dependency**: Items are packed strictly in the order of delivery (LIFO principle) to ensure accessibility.
- **Scoring Function**:
  $$ Score = x \cdot \alpha + z \cdot \beta + y $$
  Prioritizes placing items deep (min-x) and low (min-z) to maintain stability and compactness.

## 3. Strict Physical Constraint Enforcement
- **Anti-Overlap**:
  - **Logic**: Strict Axis-Aligned Bounding Box (AABB) intersection checks.
  - **Formula**: Two boxes $A$ and $B$ overlap iff:
    $$ \neg (A_{x2} \le B_{x1} \lor A_{x1} \ge B_{x2} \lor A_{y2} \le B_{y1} \lor A_{y1} \ge B_{y2} \lor A_{z2} \le B_{z1} \lor A_{z1} \ge B_{z2}) $$
- **Anti-Floating (Stability)**:
  - **Support Ratio**: Requires 100% of the item's base area to be supported by the floor or other items ($S_{ratio} = 1.0$).
  - **Corner Support**: Explicitly validates that all 4 corners of the item's base are supported to prevent tipping.
  - **Height Map**: Maintains a discretized grid of the packing space's current height surface for $O(1)$ support queries.

## 4. Acceleration & Optimization Strategies
- **Vectorized Collision Detection**: Replaced $O(N)$ loop-based collision checks with Numpy broadcasting, enabling parallel comparison of a candidate item against all placed items simultaneously.
- **Heuristic Support Pruning**: Implemented a "Corner Pre-check" strategy. Before performing expensive area-based support calculations, the algorithm checks the 4 corners. If any corner is unsupported, the position is immediately rejected, pruning ~90% of invalid attempts.
- **Memory Optimization**: Utilized `float32` and pre-allocated Numpy matrices for storage to reduce memory overhead and garbage collection frequency during massive iterations.
- **Caching Mechanism**: Memoizes packing results for route subsequences to avoid redundant computations for identical partial routes.
