import math
import numpy as np
import random
from data_model import Node, Item, VehicleType, Route, Solution
from fleet_manager import FleetManager
from alns_operators import ALNSOperators
from alns_solver import ALNSSolver
from config import Config

# --- 1. 数据生成 ---
def create_test_data():
    print("Generating test data...")
    
    # Depot
    depot = Node(id=0, is_bonded=False, x=0, y=0)
    
    # Customers
    # Node 1: Bonded Warehouse (Must be first)
    node1 = Node(id=1, is_bonded=True, x=50, y=0) 
    # Node 2-4: Normal Customers
    node2 = Node(id=2, is_bonded=False, x=100, y=0)
    node3 = Node(id=3, is_bonded=False, x=100, y=50)
    node4 = Node(id=4, is_bonded=False, x=50, y=50)
    
    nodes = [depot, node1, node2, node3, node4]
    
    # Items
    # 尺寸单位: mm
    # Item(id, l, w, h, weight)
    
    # Node 1 (Bonded): Large items
    node1.items.append(Item("N1-I1", 1000, 1000, 1000, 100))
    node1.items.append(Item("N1-I2", 1000, 1000, 1000, 100))
    
    # Node 2: Small items
    node2.items.append(Item("N2-I1", 500, 500, 500, 20))
    node2.items.append(Item("N2-I2", 500, 500, 500, 20))
    
    # Node 3: Long items
    node3.items.append(Item("N3-I1", 2000, 500, 500, 50))
    
    # Node 4: Mixed
    node4.items.append(Item("N4-I1", 800, 800, 800, 40))

    # Vehicles
    # Type A: Small (4.2m) -> 4200 x 1800 x 1800 (Example)
    v1 = VehicleType("SmallTruck", 4200, 1800, 1800, 2000)
    # Type B: Large (7.6m) -> 7600 x 2400 x 2400
    v2 = VehicleType("LargeTruck", 7600, 2400, 2400, 5000)
    
    vehicle_types = [v1, v2]
    
    # Distance Matrix
    n_nodes = len(nodes)
    dist_matrix = np.zeros((n_nodes, n_nodes))
    for i in range(n_nodes):
        for j in range(n_nodes):
            d = math.sqrt((nodes[i].x - nodes[j].x)**2 + (nodes[i].y - nodes[j].y)**2)
            dist_matrix[i][j] = d
            
    return nodes, vehicle_types, dist_matrix

# --- 2. 主程序 ---
def main():
    # Setup
    nodes, v_types, dist_mtx = create_test_data()
    depot = nodes[0]
    customers = nodes[1:]
    
    fleet_mgr = FleetManager(v_types, dist_mtx)
    ops = ALNSOperators(fleet_mgr)
    
    # Initial Solution
    print("Constructing initial solution...")
    initial_sol = Solution(depot)
    initial_sol = ops.greedy_insertion(initial_sol, customers) # Insert all customers
    
    print(f"Initial Solution: {len(initial_sol.routes)} routes")
    for i, r in enumerate(initial_sol.routes):
        print(f"  Route {i}: {[n.id for n in r.sequence]} | Vehicle: {r.vehicle.type_id} | Load: {r.load_rate:.2%}")

    # ALNS Loop
    print("\nStarting ALNS Solver...")
    print(f"Operators Loaded: {len(ops.destroy_ops)} Destroy, {len(ops.repair_ops)} Repair")
    
    solver = ALNSSolver(initial_sol, ops)
    best_sol = solver.solve()
    
    print("\n=== Final Results ===")
    print(f"Best Solution Objective: {solver._objective(best_sol):.4f}")
    for i, r in enumerate(best_sol.routes):
        print(f"Route {i}:")
        print(f"  Sequence: {[n.id for n in r.sequence]}")
        print(f"  Vehicle: {r.vehicle.type_id}")
        print(f"  Load Rate: {r.load_rate:.2%}")
        print(f"  Dist Cost: {r.dist_cost:.2f}")
        print(f"  Is Bonded Route: {any(n.is_bonded for n in r.sequence)}")
        
        # 验证 Bonded 约束
        bonded_indices = [idx for idx, n in enumerate(r.sequence) if n.is_bonded]
        if bonded_indices:
            print(f"  [Check] Bonded Node Indices: {bonded_indices}")
            if bonded_indices[0] == 1:
                print("  [PASS] Bonded constraint satisfied (Index 1)")
            else:
                print("  [FAIL] Bonded constraint violated!")
        
        print("  Packed Items (First 5):")
        for pi in r.packed_items[:5]:
            print(f"    - {pi.item.id}: ({pi.x}, {pi.y}, {pi.z}) size {pi.lx}x{pi.ly}x{pi.lz}")

if __name__ == "__main__":
    main()
