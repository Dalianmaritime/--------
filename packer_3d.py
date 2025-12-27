"""
3D Bin Packing
--------------
Purpose: Implements the 3D packing heuristic (Sequence Dependent).
Key Logic:
- Sequence Dependent: Packs items strictly in the order of node visitation.
- Corner Point Heuristic: Places items at the best available corner (min X, min Z).
- Constraints: Checks boundaries, collisions, and support surface (80%).
- Caching: Caches packing results by route signature to improve performance.
"""
from config import Config
from geometry_kernel import HeightMap, check_aabb_collision
from data_model import Route, PackedItem

class SequenceDependentPacker:
    def __init__(self):
        # 缓存字典
        self.cache = {}

    def pack(self, route: Route) -> bool:
        """
        对路径进行全量装箱模拟。
        """
        # 1. 缓存命中检查
        if Config.ENABLE_CACHE and route.signature in self.cache:
            res = self.cache[route.signature]
            if res['feasible']:
                route.packed_items = res['items']
                route.load_rate = res['rate']
                return True
            return False

        # 2. 初始化环境
        # 极点列表，初始为 (0,0,0)
        extreme_points = [(0, 0, 0)]
        placed_items = []
        height_map = HeightMap(route.vehicle.L, route.vehicle.W)
        
        # 3. 序列化装箱循环
        # 关键：跳过 Depot，严格按 Sequence 顺序装
        for node in route.sequence:
            if node.id == 0: continue # Skip Depot
            
            # 站点内启发式：大件优先 (Best Fit Decreasing)
            sorted_items = sorted(node.items, key=lambda i: i.l*i.w*i.h, reverse=True)
            
            for item in sorted_items:
                best_pos = None
                best_score = float('inf')
                
                # 遍历所有极点
                for ep in extreme_points:
                    for rot in item.orientations:
                        l, w, h = rot
                        
                        # --- 约束检查 ---
                        # A. 车辆边界
                        if ep[0]+l > route.vehicle.L or ep[1]+w > route.vehicle.W or ep[2]+h > route.vehicle.H:
                            continue
                            
                        # B. 碰撞检查 (与 placed_items)
                        if check_aabb_collision((ep[0], ep[1], ep[2], l, w, h), placed_items):
                            continue
                            
                        # C. 支撑检查 (仅当悬空时)
                        if ep[2] > 0:
                            if not height_map.check_support(ep[0], ep[1], l, w, ep[2]):
                                continue
                        
                        # --- 评分策略 (Corner Point Heuristic) ---
                        # 核心：优先 x 小 (里侧)，z 小 (下侧)
                        # 这天然满足了题目 "先访问的货物装在里侧" 的约束
                        score = ep[0] * 1000 + ep[2] * 100 + ep[1]
                        
                        if score < best_score:
                            best_score = score
                            best_pos = (ep, l, w, h)
                
                if best_pos:
                    # 放置货物
                    ep, l, w, h = best_pos
                    new_packed = PackedItem(item, ep[0], ep[1], ep[2], l, w, h)
                    placed_items.append(new_packed)
                    
                    # 更新数据结构
                    height_map.update(ep[0], ep[1], l, w, ep[2] + h)
                    self._update_extreme_points(extreme_points, ep[0], ep[1], ep[2], l, w, h)
                    extreme_points.sort(key=lambda p: p[0]) # 保持有序加速搜索
                else:
                    # 失败：写入缓存并返回
                    self.cache[route.signature] = {'feasible': False}
                    return False

        # 4. 成功：计算装载率并缓存
        load_rate = self._calc_load_rate(placed_items, route.vehicle)
        self.cache[route.signature] = {
            'feasible': True, 'items': placed_items, 'rate': load_rate
        }
        route.packed_items = placed_items
        route.load_rate = load_rate
        return True

    def _update_extreme_points(self, eps, x, y, z, l, w, h):
        """
        极点更新逻辑 (简化版)
        1. 移除被新盒子覆盖的极点
        2. 生成新极点：(x+l, y, z), (x, y+w, z), (x, y, z+h)
        """
        new_eps = []
        # 简单的生成策略：添加3个角点
        candidates = [
            (x + l, y, z),
            (x, y + w, z),
            (x, y, z + h)
        ]
        
        # 引入 Epsilon 避免浮点误差导致的误删
        EPS = 1e-4

        # 移除失效点
        for ep in eps:
            # 如果 ep 在新盒子内部或边界上，则移除
            # 使用 EPS 收缩盒子范围，确保只有严格在内部(或边界)的点被移除
            # 逻辑：如果点在 Box 范围内，则移除。
            # Box range: [x, x+l], [y, y+w], [z, z+h]
            # 为了防止数值误差导致本来在表面的点被误判为内部，
            # 我们应该让 Box 稍微 "小" 一点点？
            # 不，如果是为了移除“被覆盖”的点。
            # 如果点在 (x, y, z)，新盒子在 (x, y, z) 放下。点被覆盖。
            # 判断条件: ep >= x AND ep < x+l.
            # 加上 EPS: ep >= x - EPS AND ep < x + l - EPS ?
            # 稳健做法：
            if not (ep[0] >= x - EPS and ep[0] < x + l - EPS and 
                    ep[1] >= y - EPS and ep[1] < y + w - EPS and 
                    ep[2] >= z - EPS and ep[2] < z + h - EPS):
                new_eps.append(ep)
        
        # 添加新点 (需过滤掉超出车厢的点)
        for c in candidates:
            # 这里可以添加投影逻辑，将悬空点投影到最近的物体表面
            new_eps.append(c)
            
        # 去重
        eps[:] = list(set(new_eps))

    def _calc_load_rate(self, items, vehicle):
        """
        计算装载率 = 货物总体积 / 车厢体积
        """
        if not items:
            return 0.0
        
        total_item_vol = sum(i.lx * i.ly * i.lz for i in items)
        vehicle_vol = vehicle.L * vehicle.W * vehicle.H
        
        return total_item_vol / vehicle_vol if vehicle_vol > 0 else 0.0