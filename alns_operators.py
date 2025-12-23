import random
import math
from copy import deepcopy
from data_model import Route, Solution
from config import Config

class ALNSOperators:
    def __init__(self, fleet_manager):
        self.fleet_mgr = fleet_manager
        
        # 注册算子列表
        self.destroy_ops = [
            self.random_removal,
            self.worst_removal,
            self.shaw_removal
        ]
        self.repair_ops = [
            self.greedy_insertion,
            self.regret_2_insertion
        ]

    def _calculate_weighted_cost(self, route):
        """Helper to calculate weighted cost for a route"""
        return Config.ALPHA * (1 - route.load_rate) + Config.BETA * route.dist_cost

    # --- Destroy Operators ---

    def random_removal(self, solution, n_remove=None):
        """随机移除 N 个节点"""
        new_sol = solution.copy()
        
        # 收集所有客户点
        all_nodes = []
        for r in new_sol.routes:
            all_nodes.extend(r.sequence[1:-1])
            
        if not all_nodes:
            return new_sol, []
            
        # 确定移除数量 (默认随机 10%~40%)
        if n_remove is None:
            n_remove = random.randint(1, max(1, len(all_nodes) // 2))
        n_remove = min(n_remove, len(all_nodes))
        
        # 随机选择
        removed_nodes = random.sample(all_nodes, n_remove)
        
        # 重建 Solution
        self._rebuild_solution(new_sol, removed_nodes)
        return new_sol, removed_nodes

    def worst_removal(self, solution, n_remove=None):
        """最差成本移除：移除那些导致目标函数值增加最多的点"""
        new_sol = solution.copy()
        all_nodes = []
        node_costs = [] # (node, cost_saving)
        
        for r in new_sol.routes:
            # 计算移除每个点后的节约值
            seq = r.sequence
            if len(seq) <= 2: continue
            
            # 计算当前路径的加权成本
            current_cost = self._calculate_weighted_cost(r)
            
            for i in range(1, len(seq)-1):
                node = seq[i]
                # 构造移除该点后的临时序列
                temp_seq = seq[:i] + seq[i+1:]
                
                # 重新评估该路径 (使用最小车型)
                temp_route = self.fleet_mgr.find_best_vehicle(temp_seq)
                
                if temp_route:
                    new_cost = self._calculate_weighted_cost(temp_route)
                    saving = current_cost - new_cost
                    node_costs.append((node, saving))
                else:
                    # 如果移除点后反而不可行(理论上不应该)，则忽略
                    pass
        
        # 排序：saving 越大，说明该点导致成本增加越多，越应该被移除
        node_costs.sort(key=lambda x: x[1], reverse=True)
        
        if not node_costs:
            return new_sol, []

        if n_remove is None:
            n_remove = random.randint(1, max(1, len(node_costs) // 2))
        n_remove = min(n_remove, len(node_costs))
        
        # 引入随机性 (比如取前 2*N 中随机 N 个，或者概率选择)
        limit = min(len(node_costs), n_remove * 2)
        candidates = node_costs[:limit]
        selected = random.sample(candidates, n_remove)
        removed_nodes = [x[0] for x in selected]
        
        self._rebuild_solution(new_sol, removed_nodes)
        return new_sol, removed_nodes

    def shaw_removal(self, solution, n_remove=None):
        """
        Shaw Removal (Relatedness Removal)
        移除互相关联度高的点（距离近、需求量相似）
        R(i, j) = φ1 * (d_ij / max_dist) + φ2 * (|vol_i - vol_j| / max_vol_diff)
        """
        new_sol = solution.copy()
        all_nodes = []
        for r in new_sol.routes:
            all_nodes.extend(r.sequence[1:-1])
            
        if not all_nodes:
            return new_sol, []

        if n_remove is None:
            n_remove = random.randint(1, max(1, len(all_nodes) // 2))
        n_remove = min(n_remove, len(all_nodes))
        
        # 预计算最大距离和最大体积差用于归一化
        max_dist = 1.0
        max_vol_diff = 1.0
        
        # 简单采样估算最大值，避免 O(N^2)
        sample_size = min(len(all_nodes), 50)
        sample_nodes = random.sample(all_nodes, sample_size)
        for i in range(len(sample_nodes)):
            for j in range(i+1, len(sample_nodes)):
                d = self.fleet_mgr.get_distance(sample_nodes[i], sample_nodes[j])
                v_i = sum(it.l*it.w*it.h for it in sample_nodes[i].items)
                v_j = sum(it.l*it.w*it.h for it in sample_nodes[j].items)
                v_diff = abs(v_i - v_j)
                max_dist = max(max_dist, d)
                max_vol_diff = max(max_vol_diff, v_diff)
        
        # 1. 随机选一个种子点
        seed_node = random.choice(all_nodes)
        removed_nodes = [seed_node]
        remain_pool = [n for n in all_nodes if n != seed_node]
        
        # 2. 循环寻找与已移除点最相关的点
        while len(removed_nodes) < n_remove and remain_pool:
            # 随机选一个已移除的点作为参考
            ref_node = random.choice(removed_nodes)
            
            # 计算相关性 (数值越小越相关)
            candidates = []
            ref_vol = sum(it.l*it.w*it.h for it in ref_node.items)
            
            for target in remain_pool:
                # 距离项
                dist = self.fleet_mgr.get_distance(ref_node, target)
                # 体积项
                target_vol = sum(it.l*it.w*it.h for it in target.items)
                vol_diff = abs(ref_vol - target_vol)
                
                # 归一化计算相关性
                score = (dist / max_dist) + (vol_diff / max_vol_diff)
                candidates.append((target, score))
            
            # 排序选最小的
            candidates.sort(key=lambda x: x[1])
            
            # 引入随机性
            idx = int(random.random()**3 * len(candidates))
            selected = candidates[idx][0]
            
            removed_nodes.append(selected)
            remain_pool.remove(selected)
            
        self._rebuild_solution(new_sol, removed_nodes)
        return new_sol, removed_nodes

    def _rebuild_solution(self, solution, removed_nodes):
        """辅助函数：从 solution 中物理移除节点，并重建 Route 对象"""
        removed_ids = set(n.id for n in removed_nodes)
        new_routes = []
        
        for r in solution.routes:
            # 检查该路径是否有节点被移除
            original_node_ids = set(n.id for n in r.sequence[1:-1])
            if not original_node_ids.intersection(removed_ids):
                # 路径未受影响，直接保留
                new_routes.append(r)
                continue
                
            # 路径受影响，需要重建
            new_seq = [solution.start_node]
            for node in r.sequence[1:-1]:
                if node.id not in removed_ids:
                    new_seq.append(node)
            new_seq.append(solution.end_node)
            
            if len(new_seq) > 2:
                # 重新评估该路径 (车型可能会变小)
                new_route = self.fleet_mgr.find_best_vehicle(new_seq)
                if new_route:
                    new_routes.append(new_route)
                else:
                    # 理论上不应该发生，除非移除点导致剩余点无法用任何车装载(极不可能)
                    pass
        
        solution.routes = new_routes

    # --- Repair Operators ---

    def greedy_insertion(self, solution, removed_nodes):
        """贪婪插入：每次选择目标函数值增量最小的插入位置"""
        random.shuffle(removed_nodes) # 随机顺序插入
        
        for node in removed_nodes:
            self._insert_node_greedy(solution, node)
            
        return solution

    def regret_2_insertion(self, solution, removed_nodes):
        """
        Regret-2 插入：
        对于每个未分配节点，计算 (次优插入成本 - 最优插入成本) = Regret 值。
        优先插入 Regret 值最大的节点。
        """
        remain_nodes = list(removed_nodes)
        
        while remain_nodes:
            best_regret_node = None
            max_regret_val = -1
            best_insert_move = None # (node, route_idx, insert_pos, cost_inc)
            
            for node in remain_nodes:
                # 寻找该节点在所有路径的所有可行位置的 Cost
                candidates = self._find_all_insertion_costs(solution, node)
                
                # 补充：开启新车的 Cost
                # 必须真实计算新车的加权成本
                new_route = self.fleet_mgr.find_best_vehicle([solution.start_node, node, solution.end_node])
                if new_route:
                    new_cost = self._calculate_weighted_cost(new_route)
                    # 增量即为新车的总成本
                    candidates.append((new_cost, -1, 1)) 
                
                # 排序
                candidates.sort(key=lambda x: x[0])
                
                if not candidates:
                    continue
                    
                best_cost = candidates[0][0]
                second_best_cost = candidates[1][0] if len(candidates) > 1 else float('inf')
                
                regret = second_best_cost - best_cost
                
                if regret > max_regret_val:
                    max_regret_val = regret
                    best_regret_node = node
                    r_idx, pos = candidates[0][1], candidates[0][2]
                    best_insert_move = (r_idx, pos)
            
            # 执行最佳移动
            if best_regret_node and best_insert_move:
                r_idx, pos = best_insert_move
                if r_idx == -1:
                    # 新建路径
                    new_route = self.fleet_mgr.find_best_vehicle([solution.start_node, best_regret_node, solution.end_node])
                    solution.routes.append(new_route)
                else:
                    # 插入现有路径
                    route = solution.routes[r_idx]
                    new_seq = route.sequence[:pos] + [best_regret_node] + route.sequence[pos:]
                    new_route = self.fleet_mgr.find_best_vehicle(new_seq)
                    solution.routes[r_idx] = new_route
                
                remain_nodes.remove(best_regret_node)
            else:
                break
                
        return solution

    # --- Helpers ---

    def _insert_node_greedy(self, solution, node):
        best_cost_inc = float('inf')
        best_pos = None # (r_idx, pos, new_route)
        
        # 1. 尝试插入现有路径
        for r_idx, route in enumerate(solution.routes):
            # 一维容量预检 (剪枝)
            if not self._check_capacity_feasible(route, node):
                continue

            # 约束检查：Bonded Warehouse
            if node.is_bonded:
                possible_indices = [1] # 必须在 Start(0) 之后
            else:
                # 如果现有路径已有 Bonded，只能插在它后面
                start = 2 if (len(route.sequence) > 1 and route.sequence[1].is_bonded) else 1
                # 必须在 End Node 之前，End Node 索引是 len-1，所以 range 止于 len
                # insert(i, node) 意味着在 i 处插入，原 i 后移。
                # 最后一个有效插入位置是 len-1 (即在 End Node 之前)
                possible_indices = range(start, len(route.sequence))
                
            current_weighted_cost = self._calculate_weighted_cost(route)
            
            for i in possible_indices:
                new_seq = route.sequence[:i] + [node] + route.sequence[i:]
                new_route = self.fleet_mgr.find_best_vehicle(new_seq)
                
                if new_route:
                    new_weighted_cost = self._calculate_weighted_cost(new_route)
                    inc = new_weighted_cost - current_weighted_cost
                    if inc < best_cost_inc:
                        best_cost_inc = inc
                        best_pos = (r_idx, i, new_route)
        
        # 2. 尝试开启新车
        new_route_single = self.fleet_mgr.find_best_vehicle([solution.start_node, node, solution.end_node])
        if new_route_single:
            # 新车的增量就是其加权成本
            new_cost = self._calculate_weighted_cost(new_route_single)
            if new_cost < best_cost_inc:
                best_cost_inc = new_cost
                best_pos = (-1, 1, new_route_single)
        
        # 执行插入
        if best_pos:
            r_idx, i, res_route = best_pos
            if r_idx == -1:
                solution.routes.append(res_route)
            else:
                solution.routes[r_idx] = res_route

    def _find_all_insertion_costs(self, solution, node):
        """返回所有可行插入位置的 [(cost_inc, route_idx, pos), ...]"""
        costs = []
        for r_idx, route in enumerate(solution.routes):
            # 一维容量预检 (剪枝)
            if not self._check_capacity_feasible(route, node):
                continue

            if node.is_bonded:
                indices = [1]
            else:
                start = 2 if (len(route.sequence) > 1 and route.sequence[1].is_bonded) else 1
                indices = range(start, len(route.sequence))
            
            current_weighted_cost = self._calculate_weighted_cost(route)
            
            for i in indices:
                new_seq = route.sequence[:i] + [node] + route.sequence[i:]
                new_route = self.fleet_mgr.find_best_vehicle(new_seq)
                if new_route:
                    new_weighted_cost = self._calculate_weighted_cost(new_route)
                    inc = new_weighted_cost - current_weighted_cost
                    costs.append((inc, r_idx, i))
        return costs

    def _check_capacity_feasible(self, route, node):
        """快速检查一维容量约束 (重量/体积)"""
        # 假设 route.vehicle 是当前路径使用的车型
        # 我们需要检查加入 node 后，是否有可能装入最大的车型
        # 获取车队中最大的载重和体积
        max_v_type = self.fleet_mgr.vehicle_types[-1] # 假设已按体积排序
        
        current_weight = sum(item.weight for n in route.sequence for item in n.items)
        node_weight = sum(item.weight for item in node.items)
        
        if current_weight + node_weight > max_v_type.max_weight:
            return False
            
        # 粗略体积检查 (所有item体积之和 < 车厢体积)
        current_vol = sum(item.l*item.w*item.h for n in route.sequence for item in n.items)
        node_vol = sum(item.l*item.w*item.h for item in node.items)
        
        if current_vol + node_vol > max_v_type.volume:
            return False
            
        return True
