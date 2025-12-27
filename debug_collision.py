import numpy as np
from geometry_kernel import check_aabb_collision_fast

def test_collision():
    # Setup
    N = 100
    matrix = np.zeros((N, 6), dtype=np.float32)
    placed_list = []
    
    # Place a box at [0,0,0, 10,10,10]
    box1 = [0, 0, 0, 10, 10, 10]
    matrix[0] = box1
    placed_list.append(box1)
    count = 1
    
    # Test 1: No overlap (Far away)
    new_box = (20, 20, 20, 30, 30, 30)
    res_vec = check_aabb_collision_fast(new_box, (matrix, count))
    res_list = check_aabb_collision_fast(new_box, placed_list)
    print(f"Test 1 (Far): Vec={res_vec}, List={res_list} -> {'MATCH' if res_vec == res_list else 'FAIL'}")
    
    # Test 2: Overlap (Inside)
    new_box = (2, 2, 2, 8, 8, 8)
    res_vec = check_aabb_collision_fast(new_box, (matrix, count))
    res_list = check_aabb_collision_fast(new_box, placed_list)
    print(f"Test 2 (Inside): Vec={res_vec}, List={res_list} -> {'MATCH' if res_vec == res_list else 'FAIL'}")
    
    # Test 3: Touching (Surface)
    new_box = (10, 0, 0, 20, 10, 10)
    res_vec = check_aabb_collision_fast(new_box, (matrix, count))
    res_list = check_aabb_collision_fast(new_box, placed_list)
    print(f"Test 3 (Touching): Vec={res_vec}, List={res_list} -> {'MATCH' if res_vec == res_list else 'FAIL'}")
    
    # Test 4: Slight Overlap
    new_box = (9.9, 0, 0, 19.9, 10, 10)
    res_vec = check_aabb_collision_fast(new_box, (matrix, count))
    res_list = check_aabb_collision_fast(new_box, placed_list)
    print(f"Test 4 (Slight Overlap): Vec={res_vec}, List={res_list} -> {'MATCH' if res_vec == res_list else 'FAIL'}")

if __name__ == "__main__":
    test_collision()
