"""
Geometry Kernels
----------------
Purpose: Low-level geometric calculations for 3D packing.
Key Logic:
- HeightMap: O(1) support surface detection using a discretized grid.
- check_aabb_collision: Fast Axis-Aligned Bounding Box collision detection.
"""
import numpy as np
import math
from config import Config

class HeightMap:
    """
    O(1) 复杂度的支撑检测器。
    将车厢底面网格化，map[x,y] 存储该点的最高高度。
    """
    def __init__(self, L: int, W: int):
        self.precision = Config.GRID_PRECISION
        # Ensure grid covers the entire area (ceil division)
        self.gx = math.ceil(L / self.precision)
        self.gy = math.ceil(W / self.precision)
        # 使用 float32 存储高度，防止浮点截断误差
        self.map = np.zeros((self.gx, self.gy), dtype=np.float32)

    def _get_grid_range(self, x, y, l, w):
        """
        计算覆盖的网格范围 (Inclusive of partial cells)
        使用 floor(start) 和 ceil(end) 确保覆盖所有触及的网格
        """
        p = self.precision
        ix_start = math.floor(x / p)
        iy_start = math.floor(y / p)
        ix_end = math.ceil((x + l) / p)
        iy_end = math.ceil((y + w) / p)
        return ix_start, iy_start, ix_end, iy_end

    def check_support(self, x, y, l, w, z_base):
        """
        检查在 (x,y,l,w) 区域放置高度为 z_base 的物体，支撑率是否达标。
        逻辑：
        1. 支撑面的高度必须接近 z_base (使用 EPS 容差)。
        2. 必须满足 Config.SUPPORT_RATIO (推荐 1.0)。
        3. 必须满足 4 角支撑 (防止悬臂效应)。
        """
        ix, iy, ix_end, iy_end = self._get_grid_range(x, y, l, w)
        
        # 边界检查
        if ix_end > self.gx or iy_end > self.gy: return False
        
        # --- 策略 0: 快速角点预检 (Heuristic Pruning) ---
        # 在提取大面积网格前，先检查 4 个角点。如果角点都不满足，直接失败。
        # 这能过滤掉 90% 的非法位置，避免昂贵的切片和聚合操作。
        EPS = 1e-4
        if z_base > EPS: # 地面始终支持，无需检查
            # 检查左上角
            if self.map[ix, iy] < z_base - EPS: return False
            # 检查右下角 (注意索引边界)
            if self.map[ix_end-1, iy_end-1] < z_base - EPS: return False
            # 检查右上角
            if self.map[ix, iy_end-1] < z_base - EPS: return False
            # 检查左下角
            if self.map[ix_end-1, iy] < z_base - EPS: return False

        # 获取区域高度切片
        region = self.map[ix:ix_end, iy:iy_end]
        
        # --- 策略 1: 面积支撑 (Fast Numpy Optimization) ---
        
        # 地面始终支持
        if z_base < EPS:
            return True
            
        # 快速检查：如果区域为空，直接返回 False (除非 z_base 也是 0，已处理)
        if region.size == 0: return False

        # 优化：如果是 100% 支撑要求，可以使用 Min/Max 快速验证
        # 要求所有点的高度都近似等于 z_base
        if Config.SUPPORT_RATIO >= 0.99:
            r_min = np.min(region)
            # 如果最小高度过低 -> 悬空
            if r_min < z_base - EPS:
                return False
                
            r_max = np.max(region)
            # 如果最大高度过高 -> 表面不平整 (或者嵌入了物体)
            if r_max > z_base + EPS:
                return False
            
            # 如果 min 和 max 都在容差范围内，则全都在范围内
            return True
        else:
            # 传统的 Mask 统计 (较慢，用于非 100% 支撑)
            support_mask = np.abs(region - z_base) < EPS
            support_cells = np.sum(support_mask)
            total_cells = region.size
            
            area_ratio = support_cells / total_cells
            if area_ratio < Config.SUPPORT_RATIO:
                return False

            # --- 策略 2: 四角支撑 (Corner Support) ---
            # 仅在非 100% 支撑模式下需要显式检查四角 (100% 模式下 min/max 已保证)
            rows, cols = region.shape
            corners = [
                (0, 0),
                (0, cols - 1),
                (rows - 1, 0),
                (rows - 1, cols - 1)
            ]
            for r, c in corners:
                if not support_mask[r, c]:
                    return False
            return True

    def get_max_height(self, x, y, l, w):
        """获取区域内的最大高度 (用于快速碰撞剔除)"""
        ix, iy, ix_end, iy_end = self._get_grid_range(x, y, l, w)
        if ix_end > self.gx or iy_end > self.gy: return float('inf') # Out of bounds
        region = self.map[ix:ix_end, iy:iy_end]
        if region.size == 0: return 0.0
        return np.max(region)

    def update(self, x, y, l, w, z_top):
        """更新区域高度"""
        ix, iy, ix_end, iy_end = self._get_grid_range(x, y, l, w)
        # 边界保护
        ix_end = min(ix_end, self.gx)
        iy_end = min(iy_end, self.gy)
        self.map[ix:ix_end, iy:iy_end] = z_top

def check_aabb_collision(new_box, placed_boxes):
    """
    简单的 AABB 碰撞检测 (兼容旧接口)
    """
    EPS = 1e-4
    nx, ny, nz, nl, nw, nh = new_box
    for p in placed_boxes:
        if (nx < p.x + p.lx - EPS and nx + nl > p.x + EPS and
            ny < p.y + p.ly - EPS and ny + nw > p.y + EPS and
            nz < p.z + p.lz - EPS and nz + nh > p.z + EPS):
            return True
    return False

def check_aabb_collision_vectorized(new_aabb, placed_items_matrix, count):
    """
    Vectorized AABB Collision Detection using Numpy.
    
    Args:
        new_aabb: tuple (x1, y1, z1, x2, y2, z2)
        placed_items_matrix: numpy array of shape (N, 6) or larger
        count: integer, number of valid items in matrix
    
    Returns:
        bool: True if collision detected, False otherwise
    """
    if count == 0:
        return False
        
    EPS = 1e-4
    nx1, ny1, nz1, nx2, ny2, nz2 = new_aabb
    
    # Slice valid items
    valid_items = placed_items_matrix[:count]
    
    # Vectorized Overlap Check
    # Overlap condition: not (A.end <= B.start or A.start >= B.end)
    # Inverse: A.end > B.start and A.start < B.end
    
    # X axis overlap: new.x2 > item.x1 and new.x1 < item.x2
    # But wait, placed_items_matrix columns: x1, y1, z1, x2, y2, z2
    # Columns: 0=x1, 1=y1, 2=z1, 3=x2, 4=y2, 5=z2
    
    # We want:
    # x_overlap = (nx2 > items[:, 0] + EPS) & (nx1 < items[:, 3] - EPS)
    # y_overlap = (ny2 > items[:, 1] + EPS) & (ny1 < items[:, 4] - EPS)
    # z_overlap = (nz2 > items[:, 2] + EPS) & (nz1 < items[:, 5] - EPS)
    
    # Collision = x_overlap & y_overlap & z_overlap
    
    # Using np.any to check if ANY item collides
    
    # Optimization: Check one axis at a time and filter? 
    # No, broadcasting logic is:
    # (nx2 > x1) & (nx1 < x2) ...
    
    # Let's use strict inequalities with EPS as in loop version
    # loop: snx2 <= p[0] or snx1 >= p[3] -> NO overlap
    # overlap: not (snx2 <= p[0] or snx1 >= p[3])
    #          snx2 > p[0] and snx1 < p[3]
    
    # Using scalars vs array
    # p[0] is items[:, 0]
    
    # x_collision
    c1 = (nx2 > valid_items[:, 0] + EPS)
    c2 = (nx1 < valid_items[:, 3] - EPS)
    
    # If any fail x check, they are not colliding.
    # We only care if ALL checks pass for a row.
    
    # Combine:
    # collision_mask = (x_col) & (y_col) & (z_col)
    
    x_col = c1 & c2
    if not np.any(x_col): return False # Early exit if no X overlap
    
    y_col = (ny2 > valid_items[:, 1] + EPS) & (ny1 < valid_items[:, 4] - EPS)
    xy_col = x_col & y_col
    if not np.any(xy_col): return False
    
    z_col = (nz2 > valid_items[:, 2] + EPS) & (nz1 < valid_items[:, 5] - EPS)
    
    return np.any(xy_col & z_col)

def check_aabb_collision_fast(new_aabb, placed_aabbs):
    """
    Wrapper for compatibility. If placed_aabbs is list, use loop.
    If placed_aabbs is tuple (matrix, count), use vectorized.
    """
    if isinstance(placed_aabbs, tuple):
        return check_aabb_collision_vectorized(new_aabb, placed_aabbs[0], placed_aabbs[1])
    
    # Fallback to loop for list
    EPS = 1e-4
    nx1, ny1, nz1, nx2, ny2, nz2 = new_aabb
    
    snx1, sny1, snz1 = nx1 + EPS, ny1 + EPS, nz1 + EPS
    snx2, sny2, snz2 = nx2 - EPS, ny2 - EPS, nz2 - EPS
    
    for p in placed_aabbs:
        if snx2 <= p[0] or snx1 >= p[3]: continue
        if sny2 <= p[1] or sny1 >= p[4]: continue
        if snz2 <= p[2] or snz1 >= p[5]: continue
        return True
    return False
