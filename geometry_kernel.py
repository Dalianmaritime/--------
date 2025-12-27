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
        
        # 获取区域高度切片
        region = self.map[ix:ix_end, iy:iy_end]
        
        # --- 策略 1: 面积支撑 ---
        # 统计提供有效支撑的网格数 (abs(height - z_base) < 1e-4)
        EPS = 1e-4
        # 支持: 高度接近 z_base
        # 允许地面 (z_base=0) 放置
        if z_base < EPS:
            return True
            
        support_mask = np.abs(region - z_base) < EPS
        support_cells = np.sum(support_mask)
        total_cells = region.size
        
        if total_cells == 0: return False
        
        area_ratio = support_cells / total_cells
        if area_ratio < Config.SUPPORT_RATIO:
            return False

        # --- 策略 2: 四角支撑 (Corner Support) ---
        # 检查四个角的网格是否提供支撑
        # 左上 (0,0), 右上 (w-1, 0), 左下 (0, h-1), 右下 (w-1, h-1)
        # 注意 region 是 [lx, ly]
        rows, cols = region.shape
        corners = [
            (0, 0),
            (0, cols - 1),
            (rows - 1, 0),
            (rows - 1, cols - 1)
        ]
        
        for r, c in corners:
            # 只要有一个角悬空，则视为不稳定 (Strict Mode)
            if not support_mask[r, c]:
                return False
                
        return True

    def update(self, x, y, l, w, z_top):
        """更新区域高度"""
        ix, iy, ix_end, iy_end = self._get_grid_range(x, y, l, w)
        # 边界保护
        ix_end = min(ix_end, self.gx)
        iy_end = min(iy_end, self.gy)
        self.map[ix:ix_end, iy:iy_end] = z_top

def check_aabb_collision(new_box, placed_boxes):
    """
    简单的 AABB 碰撞检测
    引入 Epsilon 防止浮点数误差导致的重叠漏判
    """
    EPS = 1e-4
    nx, ny, nz, nl, nw, nh = new_box
    for p in placed_boxes:
        # 检查是否重叠: 两个区间 [a, b] 和 [c, d] 重叠当且仅当 a < d 且 c < b
        # 这里加上 EPS 收缩判断条件，使得只有真正显著的重叠才被捕获？
        # 不，我们要防止重叠，所以要严格。
        # 如果 gap < EPS，认为接触。
        # 如果 overlap > EPS，认为碰撞。
        
        # 逆向思维：如果不重叠 (Has Gap)
        # gap_x = (nx >= p.x + p.lx - EPS) or (nx + nl <= p.x + EPS)
        # 如果 not gap -> Collision
        
        if (nx < p.x + p.lx - EPS and nx + nl > p.x + EPS and
            ny < p.y + p.ly - EPS and ny + nw > p.y + EPS and
            nz < p.z + p.lz - EPS and nz + nh > p.z + EPS):
            return True
    return False
