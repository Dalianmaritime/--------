"""
Global Configuration
--------------------
Purpose: Centralizes all tunable parameters for the algorithm and physical constraints.
Key Parameters:
- Physical: Support ratio (0.8), Grid precision (50mm).
- Objective: Alpha (Load Rate Weight), Beta (Distance Weight).
- ALNS: Iterations, Cooling Rate, Destroy/Repair operators weights.
"""
class Config:
    # --- 物理约束 ---
    SUPPORT_RATIO = 1.0       # 支撑面积阈值 (严格要求 100% 支撑，消除悬空)
    GRID_PRECISION = 1        # 高度图网格精度 (mm), 降低精度值以消除浮空误差
    
    # --- 目标函数 (归一化权重) ---
   
    ALPHA = 100000.0         # 装载率权重 (大幅提升以匹配距离量纲)
    BETA = 1.0                # 距离权重
    LAMBDA_W = 0.5            # 质量装载率权重
    LAMBDA_V = 0.5            # 体积装载率权重

    # --- ALNS 算法参数 ---
    MAX_ITERATIONS = 5000     # 最大迭代
    MAX_RUNTIME = 3600        # 秒
    SEGMENT_SIZE = 100        # 权重更新周期
    
    # --- 模拟退火 ---
    START_TEMP = 100.0
    COOLING_RATE = 0.9995
    
    # --- 性能优化 ---
    ENABLE_CACHE = True       # 开启装箱缓存 (核心加速开关)