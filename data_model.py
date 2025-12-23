from dataclasses import dataclass, field
from typing import List, Tuple
import hashlib

@dataclass(frozen=True)
class Item:
    """货物实体：不可变对象，支持哈希"""
    id: str
    l: int
    w: int
    h: int
    weight: float
    # 预计算6种旋转形态 (l,w,h)
    orientations: Tuple[Tuple[int, int, int], ...] = field(init=False, hash=False)

    def __post_init__(self):
        # 生成6种旋转排列
        perms = set([
            (self.l, self.w, self.h), (self.l, self.h, self.w),
            (self.w, self.l, self.h), (self.w, self.h, self.l),
            (self.h, self.l, self.w), (self.h, self.w, self.l)
        ])
        object.__setattr__(self, 'orientations', tuple(perms))

@dataclass
class Node:
    id: int
    is_bonded: bool   # 保税仓硬约束
    x: float
    y: float
    items: List[Item] = field(default_factory=list)

@dataclass
class VehicleType:
    type_id: str
    L: int
    W: int
    H: int
    max_weight: float
    volume: float = field(init=False)
    
    def __post_init__(self):
        object.__setattr__(self, 'volume', self.L * self.W * self.H)

@dataclass
class PackedItem:
    """装箱结果"""
    item: Item
    x: int
    y: int
    z: int
    lx: int; ly: int; lz: int

class Route:
    """路径对象：连接路由与装箱的桥梁"""
    def __init__(self, vehicle: VehicleType, sequence: List[Node]):
        self.vehicle = vehicle
        self.sequence = sequence  # [Depot, Stop1, ..., Depot]
        
        # 结果缓存
        self.is_feasible = False
        self.packed_items: List[PackedItem] = []
        self.dist_cost = 0.0
        self.load_rate = 0.0
        self._hash = None

    @property
    def signature(self):
        """生成唯一指纹：(车型ID, 节点ID序列)"""
        if self._hash is None:
            # 只有当车型和访问顺序完全一致，装箱结果才一致
            node_ids = ",".join(str(n.id) for n in self.sequence)
            raw = f"{self.vehicle.type_id}|{node_ids}"
            self._hash = hashlib.md5(raw.encode()).hexdigest()
        return self._hash

from config import Config

class Solution:
    def __init__(self, start_node, end_node, routes=None):
        self.start_node = start_node
        self.end_node = end_node
        self.routes = routes if routes is not None else []
    
    def __repr__(self):
        return f"Solution(Routes={len(self.routes)}, Cost={self.total_cost:.2f})"
    
    @property
    def total_cost(self):
        """
        计算总加权成本：Alpha * (1 - AvgLoadRate) + Beta * TotalDistance
        """
        if not self.routes:
            return 0.0
        
        total_dist = sum(r.dist_cost for r in self.routes)
        avg_load_rate = sum(r.load_rate for r in self.routes) / len(self.routes)
        
        return Config.ALPHA * (1 - avg_load_rate) + Config.BETA * total_dist
    
    def copy(self):
        import copy
        # 浅拷贝即可，因为 Route 对象通常会被替换而不是修改
        # 但为了安全，对 routes 列表进行拷贝
        return Solution(self.start_node, self.end_node, list(self.routes))