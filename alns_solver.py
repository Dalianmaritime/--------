import numpy as np
from config import Config

class ALNSSolver:
    def __init__(self, initial_sol, operators):
        self.curr_sol = initial_sol
        self.best_sol = initial_sol
        self.ops = operators
        self.scores = np.ones(len(operators.repair_ops))

    def solve(self):
        T = Config.START_TEMP
        
        for it in range(Config.MAX_ITERATIONS):
            # 1. 轮盘赌选择算子
            repair_op = self._roulette_select(self.ops.repair_ops, self.scores)
            destroy_op = self._roulette_select(self.ops.destroy_ops)
            
            # 2. 邻域变换
            temp_sol, removed = destroy_op(self.curr_sol)
            new_sol = repair_op(temp_sol, removed)
            
            # 3. 接受准则 (Simulated Annealing)
            f_curr = self._objective(self.curr_sol)
            f_new = self._objective(new_sol)
            delta = f_new - f_curr
            
            if delta < 0 or np.random.rand() < np.exp(-delta / T):
                self.curr_sol = new_sol
                if f_new < self._objective(self.best_sol):
                    self.best_sol = new_sol
                    # 奖励算子
                    self._update_score(repair_op, reward=10)
            
            # 4. 降温
            T *= Config.COOLING_RATE
            
        return self.best_sol
    
    def _objective(self, sol):
        # 归一化处理：Alpha * (1-装载率) + Beta * 距离
        if not sol.routes:
            return float('inf')
        dist = sum(r.dist_cost for r in sol.routes)
        rate = sum(r.load_rate for r in sol.routes) / len(sol.routes)
        return Config.ALPHA * (1 - rate) + Config.BETA * dist

    def _roulette_select(self, operators, scores=None):
        """
        轮盘赌选择算子
        """
        if not operators:
            return None
            
        if scores is None:
            # 如果没有提供分数，则均匀随机选择
            return np.random.choice(operators)
            
        # 归一化分数
        total_score = np.sum(scores)
        if total_score == 0:
            probs = np.ones(len(operators)) / len(operators)
        else:
            probs = scores / total_score
            
        return np.random.choice(operators, p=probs)

    def _update_score(self, operator, reward):
        """
        更新算子分数
        这里简单实现：找到算子在列表中的索引并更新对应分数
        """
        # 注意：这里假设 operator 对象是唯一的，且 self.ops.repair_ops 是列表
        try:
            idx = self.ops.repair_ops.index(operator)
            self.scores[idx] += reward
        except ValueError:
            pass # 可能是 destroy operator，暂时不计分