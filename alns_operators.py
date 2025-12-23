import random
import math
from copy import deepcopy
from data_model import Route, Solution

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
        """最差成本移除：移除那些导致路径成本增加最多的点"""
        new_sol = solution.copy()
        all_nodes = []
        node_costs = [] # (node, cost_saving)
        
        for r in new_sol.routes:
            # 计算移除每个点后的节约值
            seq = r.sequence
            if len(seq) <= 2: continue
            
            # 原始距离
            # 注意：这里需要准确计算。为了性能，简化为距离差。
            # Cost(Full) - Cost(Removed)
            # 移除中间点 i: d(i-1, i) + d(i, i+1) - d(i-1, i+1)
            # 对于首尾点（Depot后的第一个或Depot前的最后一个），逻辑类似
            
            for i in range(1, len(seq)-1):
                node = seq[i]
                prev_node = seq[i-1]
                next_node = seq[i+1]
                
                # 计算距离 (需调用 fleet_mgr 的距离矩阵，或直接计算欧氏)
                # 假设 fleet_mgr 有 helper
                d_in = self.fleet_mgr.get_distance(prev_node, node)
                d_out = self.fleet_mgr.get_distance(node, next_node)
                d_skip = self.fleet_mgr.get_distance(prev_node, next_node)
                
                saving = d_in + d_out - d_skip
                node_costs.append((node, saving))
        
        # 排序：saving 越大，说明该点绕路越远，越应该被移除
        node_costs.sort(key=lambda x: x[1], reverse=True)
        
        if not node_costs:
            return new_sol, []

        if n_remove is None:
            n_remove = random.randint(1, max(1, len(node_costs) // 2))
        n_remove = min(n_remove, len(node_costs))
        
        # 引入随机性 (比如取前 2*N 中随机 N 个，或者概率选择)
        # 这里使用确定性 + 少量随机扰动
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
        R(i, j) = φ1 * d_ij + φ2 * |vol_i - vol_j|
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
            for target in remain_pool:
                # 距离项
                dist = self.fleet_mgr.get_distance(ref_node, target)
                # 体积项 (归一化处理，假设最大体积 10m^3 = 10^10 mm^3)
                # 简单用 log 体积差
                vol_i = sum(it.l*it.w*it.h for it in ref_node.items)
                vol_j = sum(it.l*it.w*it.h for it in target.items)
                vol_diff = abs(vol_i - vol_j)
                
                # 简化权重：距离为主，体积为辅
                score = dist + 0.00001 * vol_diff 
                candidates.append((target, score))
            
            # 排序选最小的
            candidates.sort(key=lambda x: x[1])
            
            # 引入随机性 (Power parameter p=6 in Ropke & Pisinger)
            # index = int(random.random()**p * len)
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
            new_seq = [solution.depot]
            for node in r.sequence[1:-1]:
                if node.id not in removed_ids:
                    new_seq.append(node)
            new_seq.append(solution.depot)
            
            if len(new_seq) > 2:
                # 重新评估该路径 (车型可能会变小)
                # 调用 fleet_mgr 寻找最佳车型 (Re-optimization)
                new_route = self.fleet_mgr.find_best_vehicle(new_seq)
                if new_route:
                    new_routes.append(new_route)
                else:
                    # 理论上减少点应该更可行，但如果之前是紧凑的，减少点可能导致装载率变低？
                    # 不，这里只关心可行性。减少点一定可行 (除非有最小装载率限制，暂无)
                    # 如果 find_best_vehicle 返回 None (极不可能)，保留原车型但重新计算
                    # 这里假设总是成功的
                    pass
        
        solution.routes = new_routes

    # --- Repair Operators ---

    def greedy_insertion(self, solution, removed_nodes):
        """贪婪插入：每次选择成本增量最小的插入位置"""
        # 必须拷贝，不要修改原对象
        # solution 已经在外部被 copy 过了 (在 solver 中)
        # 但为了安全... ALNS solver 传入的是 temp_sol
        
        random.shuffle(removed_nodes) # 随机顺序插入
        
        for node in removed_nodes:
            self._insert_node_greedy(solution, node)
            
        return solution

    def regret_2_insertion(self, solution, removed_nodes):
        """
        Regret-2 插入：
        对于每个未分配节点，计算 (次优插入成本 - 最优插入成本) = Regret 值。
        优先插入 Regret 值最大的节点（即如果不现在插，以后插代价最大的节点）。
        """
        remain_nodes = list(removed_nodes)
        
        while remain_nodes:
            # 计算每个节点的 Regret
            best_regret_node = None
            max_regret_val = -1
            best_insert_move = None # (node, route_idx, insert_pos, cost_inc)
            
            # 缓存每个节点的最佳和次佳位置
            # node -> [(cost, route_idx, pos), ...]
            
            for node in remain_nodes:
                # 寻找该节点在所有路径的所有可行位置的 Cost
                candidates = self._find_all_insertion_costs(solution, node)
                
                # 补充：开启新车的 Cost
                # 估算新车 Cost: 2 * dist(Depot, Node)
                dist_depot = self.fleet_mgr.get_distance(solution.depot, node)
                new_route_cost = dist_depot * 2 # 近似，忽略装载率对目标函数的影响? 
                # 实际上应该用 fleet_mgr 创建新路来算 objective。
                # 简化：假设新车总是可行的，Cost 较大。
                # 为了统一，我们尝试创建一个只包含该点的新路径
                new_route = self.fleet_mgr.find_best_vehicle([solution.depot, node, solution.depot])
                if new_route:
                    # 这里的 cost 是 Objective 吗？还是距离？
                    # Greedy 算子通常基于 Objective 增量
                    # 这里暂用 dist_cost
                    candidates.append((new_route.dist_cost, -1, 1)) # -1 表示新路径
                
                # 排序
                candidates.sort(key=lambda x: x[0])
                
                if not candidates:
                    # 无法插入任何地方（包括新车），这不应该发生
                    continue
                    
                best_cost = candidates[0][0]
                second_best_cost = candidates[1][0] if len(candidates) > 1 else float('inf')
                
                regret = second_best_cost - best_cost
                
                if regret > max_regret_val:
                    max_regret_val = regret
                    best_regret_node = node
                    # 记录最佳移动
                    r_idx, pos = candidates[0][1], candidates[0][2]
                    best_insert_move = (r_idx, pos)
            
            # 执行最佳移动
            if best_regret_node and best_insert_move:
                r_idx, pos = best_insert_move
                if r_idx == -1:
                    # 新建路径
                    new_route = self.fleet_mgr.find_best_vehicle([solution.depot, best_regret_node, solution.depot])
                    solution.routes.append(new_route)
                else:
                    # 插入现有路径
                    route = solution.routes[r_idx]
                    new_seq = route.sequence[:pos] + [best_regret_node] + route.sequence[pos:]
                    new_route = self.fleet_mgr.find_best_vehicle(new_seq)
                    solution.routes[r_idx] = new_route
                
                remain_nodes.remove(best_regret_node)
            else:
                # 无法插入？强行开新车或报错
                # 简单处理：如果无法插入，跳过（这将导致解不可行，但在 ALNS 中通常会接受不可行解并惩罚，或者强行修复）
                # 这里为了简单，假设总能开新车
                break
                
        return solution

    # --- Helpers ---

    def _insert_node_greedy(self, solution, node):
        best_cost_inc = float('inf')
        best_pos = None # (r_idx, pos, new_route)
        
        # 1. 尝试插入现有路径
        for r_idx, route in enumerate(solution.routes):
            # 约束检查：Bonded Warehouse
            if node.is_bonded:
                possible_indices = [1] # 必须在 Depot(0) 之后
            else:
                # 如果现有路径已有 Bonded，只能插在它后面
                # 假设 Bonded 永远是 index 1
                start = 2 if (len(route.sequence) > 1 and route.sequence[1].is_bonded) else 1
                possible_indices = range(start, len(route.sequence))
                
            for i in possible_indices:
                new_seq = route.sequence[:i] + [node] + route.sequence[i:]
                new_route = self.fleet_mgr.find_best_vehicle(new_seq)
                
                if new_route:
                    inc = new_route.dist_cost - route.dist_cost
                    if inc < best_cost_inc:
                        best_cost_inc = inc
                        best_pos = (r_idx, i, new_route)
        
        # 2. 尝试开启新车
        new_route_single = self.fleet_mgr.find_best_vehicle([solution.depot, node, solution.depot])
        if new_route_single:
            # 比较开启新车的成本 (通常很高) 与 现有最佳插入
            # 注意：新车的增量是整个新车的 cost
            if new_route_single.dist_cost < best_cost_inc:
                best_cost_inc = new_route_single.dist_cost
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
            if node.is_bonded:
                indices = [1]
            else:
                start = 2 if (len(route.sequence) > 1 and route.sequence[1].is_bonded) else 1
                indices = range(start, len(route.sequence))
            
            for i in indices:
                new_seq = route.sequence[:i] + [node] + route.sequence[i:]
                new_route = self.fleet_mgr.find_best_vehicle(new_seq)
                if new_route:
                    inc = new_route.dist_cost - route.dist_cost
                    costs.append((inc, r_idx, i))
        return costs
