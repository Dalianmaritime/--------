from data_model import Route
from packer_3d import SequenceDependentPacker
import math

class FleetManager:
    def __init__(self, vehicle_types, dist_matrix):
        # 按体积从小到大排序，优先尝试小车
        self.vehicle_types = sorted(vehicle_types, key=lambda v: v.volume)
        self.dist_matrix = dist_matrix
        self.packer = SequenceDependentPacker()

    def find_best_vehicle(self, sequence):
        """
        为给定的访问序列寻找能装下的最小车型。
        :param sequence: [Depot, Node1, Node2, ..., Depot]
        :return: Route 对象 (如果所有车型都装不下，返回 None)
        """
        # 1. 计算路径距离
        dist = 0.0
        for i in range(len(sequence)-1):
            u_id = sequence[i].id
            v_id = sequence[i+1].id
            # 简单的矩阵查询 (假设 dist_matrix 是 dict[u][v] 或 list[u][v])
            # 这里为了通用性，假设 dist_matrix 是 numpy array 或 list of lists，且 node.id 对应索引
            # 如果 node.id 是 str 或非连续 int，需要映射，这里假设是 int 且对应 index
            try:
                d = self.dist_matrix[u_id][v_id]
            except (IndexError, KeyError, TypeError):
                # Fallback: 简单的欧氏距离计算
                n1, n2 = sequence[i], sequence[i+1]
                d = math.sqrt((n1.x - n2.x)**2 + (n1.y - n2.y)**2)
                
            dist += d

        # 2. 遍历车型
        for v_type in self.vehicle_types:
            # 2.1 构造 Route 对象
            route = Route(v_type, sequence)
            route.dist_cost = dist
            
            # 2.2 一维预检 (重量)
            total_weight = 0
            for node in sequence:
                for item in node.items:
                    total_weight += item.weight
            
            if total_weight > v_type.max_weight:
                continue

            # 2.3 三维装箱检测
            # pack 方法会修改 route.packed_items 和 route.load_rate，并返回 True/False
            if self.packer.pack(route):
                return route
        
        return None

    def get_distance(self, n1, n2):
        """Helper to get distance between two nodes"""
        try:
            return self.dist_matrix[n1.id][n2.id]
        except (IndexError, KeyError, TypeError):
             return math.sqrt((n1.x - n2.x)**2 + (n1.y - n2.y)**2)
