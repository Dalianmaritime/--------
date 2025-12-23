import numpy as np
from config import Config

class HeightMap:
    """
    O(1) 复杂度的支撑检测器。
    将车厢底面网格化，map[x,y] 存储该点的最高高度。
    """
    def __init__(self, L: int, W: int):
        self.precision = Config.GRID_PRECISION
        self.gx = L // self.precision
        self.gy = W // self.precision
        # 使用 int16 节省内存
        self.map = np.zeros((self.gx, self.gy), dtype=np.int16)

    def check_support(self, x, y, l, w, z_base):
        """
        检查在 (x,y,l,w) 区域放置高度为 z_base 的物体，支撑率是否达标。
        逻辑：支撑面的高度必须严格等于 z_base (即紧贴物体底部)。
        """
        ix, iy = x // self.precision, y // self.precision
        il, iw = l // self.precision, w // self.precision
        
        # 边界检查
        if ix + il > self.gx or iy + iw > self.gy: return False
        
        # 获取区域高度切片
        region = self.map[ix:ix+il, iy:iy+iw]
        
        # 统计提供有效支撑的网格数 (高度 == z_base)
        support_cells = np.sum(region == z_base)
        total_cells = il * iw
        
        if total_cells == 0: return False
        return (support_cells / total_cells) >= Config.SUPPORT_RATIO

    def update(self, x, y, l, w, z_top):
        """更新区域高度"""
        ix, iy = x // self.precision, y // self.precision
        il, iw = l // self.precision, w // self.precision
        self.map[ix:ix+il, iy:iy+iw] = z_top

def check_aabb_collision(new_box, placed_boxes):
    """简单的 AABB 碰撞检测"""
    nx, ny, nz, nl, nw, nh = new_box
    for p in placed_boxes:
        if (nx < p.x + p.lx and nx + nl > p.x and
            ny < p.y + p.ly and ny + nw > p.y and
            nz < p.z + p.lz and nz + nh > p.z):
            return True
    return False
