class Config:
    # --- 物理约束 ---
    SUPPORT_RATIO = 0.8       # 支撑面积阈值 (约束 2-47)
    GRID_PRECISION = 50       # 高度图网格精度 (mm), 越小越准但内存越大
    
    # --- 目标函数 (归一化权重) ---
    # f1(装载率) 是 0-1, f2(距离) 是 1000+, 需要 Alpha 放大 f1
    ALPHA = 2000.0            # 装载率权重
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