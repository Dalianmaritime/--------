# 3L-CVRP Heuristic Solver - Project Summary

## 1. 项目简介
本项目旨在解决三维装箱约束下的车辆路径问题（3L-CVRP）。算法核心采用 **自适应大邻域搜索（ALNS）** 结合 **序列相关三维装箱启发式（Sequence Dependent 3D Packing）**，在满足复杂的物理约束（如装载率、支撑约束、LIFO顺序）的同时，优化车辆数与行驶距离。

## 2. 核心算法逻辑

### 2.1 目标函数 (Weighted Objective)
由于题目要求最大化装载率并最小化距离，且两者量纲差异巨大（装载率 0-1，距离 >10^5），我们采用了加权目标函数：
$$ \text{Cost} = \alpha \times (1 - \text{LoadRate}) + \beta \times \text{Distance} $$
- **Alpha**: 设置为 100,000+，强迫算法优先减少车辆使用（即提升单车装载率）。
- **Beta**: 设置为 1.0，用于在车辆数相同的情况下优化路径长度。

### 2.2 开放式路径 (Start -> End)
针对题目要求的“起点出发 -> 访问客户 -> 终点结束（不返回起点）”的特殊拓扑，算法做了如下适配：
- **节点映射**：Start Node ID = 0, End Node ID = N+1。
- **距离矩阵**：构建 (N+2) x (N+2) 矩阵。
- **路径构建**：所有 Route 对象强制初始化为 `[Start, ..., End]` 结构。
- **算子适配**：插入和移除算子被限制在索引 `1` 到 `len-1` 之间，严禁触碰 Start 和 End 节点。

### 2.3 ALNS 算子设计
- **Destroy Operators (破坏算子)**:
    - **Random Removal**: 随机移除，增加多样性。
    - **Worst Removal**: 移除成本增量（加权成本）最高的点。
    - **Shaw Removal**: 移除相关性（距离 + 体积差异）高的点，保留结构特征。
- **Repair Operators (修复算子)**:
    - **Greedy Insertion**: 每次选择最佳位置插入，贪婪策略。
    - **Regret-2 Insertion**: 考虑次优解与最优解的差值（后悔值），优先处理“如果不现在插，以后代价很大”的点。

### 2.4 3D 装箱策略
- **序列依赖 (Sequence Dependent)**: 严格按照车辆访问节点的顺序进行装箱，模拟真实物流场景（先装后卸）。
- **角点启发式 (Corner Point)**: 优先寻找 X 最小（最里侧）、Z 最小（最底部）的空闲空间。
- **物理约束**:
    - **支撑约束**: 使用高度图（HeightMap）网格化检测底部支撑面积是否 > 80%。
    - **一维预检**: 在调用昂贵的 3D 装箱前，先检查重量和体积总和，快速剪枝。

## 3. 项目结构说明

| 文件名 | 用途 | 关键类/函数 |
| :--- | :--- | :--- |
| **main.py** | 程序入口 | `load_problem`, `main` |
| **config.py** | 全局配置 | `Config` (Alpha, Beta, Constraints) |
| **data_loader.py** | 数据解析 | 解析 JSON，构建 Node 和 Distance Matrix |
| **data_model.py** | 数据模型 | `Solution`, `Route`, `Node`, `Item` |
| **alns_solver.py** | 算法主控 | `ALNSSolver` (SA Cooling, Weights Update) |
| **alns_operators.py** | 启发式算子 | `greedy_insertion`, `shaw_removal`, `_rebuild_solution` |
| **fleet_manager.py** | 车队管理 | `find_best_vehicle` (车型选择) |
| **packer_3d.py** | 3D 装箱核心 | `SequenceDependentPacker` |
| **geometry_kernel.py** | 几何计算 | `HeightMap` (支撑检测), `check_aabb_collision` |

## 4. 修改指南

- **调整物理约束**：修改 `config.py` 中的 `SUPPORT_RATIO` 或 `GRID_PRECISION`。
- **调整优化目标**：修改 `config.py` 中的 `ALPHA` 和 `BETA`。
- **修改装箱规则**：编辑 `packer_3d.py` 中的 `pack` 函数。
- **新增算子**：在 `alns_operators.py` 中添加函数，并在 `__init__` 中注册。

## 5. 运行方式
```bash
# 运行单个数据文件夹（批量处理）
python main.py Data
```
结果将保存在 `result/` 目录下。
