import json
import numpy as np
from typing import List, Tuple, Dict
from data_model import Node, Item, VehicleType

def load_problem(file_path: str) -> Tuple[List[Node], List[VehicleType], np.ndarray]:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 1. Parse Vehicle Types
    vehicle_types = []
    for t_dto in data['algorithmBaseParamDto']['truckTypeDtoList']:
        v = VehicleType(
            type_id=t_dto['truckTypeCode'], # Use Code as ID (e.g., CT10)
            L=int(t_dto['length']),
            W=int(t_dto['width']),
            H=int(t_dto['height']),
            max_weight=float(t_dto['maxLoad'])
        )
        vehicle_types.append(v)
    
    # 2. Parse Nodes (Platforms) & Items
    # First, collect all items by platform
    items_by_platform: Dict[str, List[Item]] = {}
    for box in data['boxes']:
        p_code = box['platformCode']
        if p_code not in items_by_platform:
            items_by_platform[p_code] = []
        
        item = Item(
            id=box['spuBoxId'],
            l=int(box['length']),
            w=int(box['width']),
            h=int(box['height']),
            weight=float(box['weight'])
        )
        items_by_platform[p_code].append(item)
    
    # Create Node objects
    # Map platformCode to Node Index
    # Index 0 is Start Point
    nodes: List[Node] = []
    
    # 1. Create Start Node (ID=0)
    start_node = Node(id=0, is_bonded=False, x=0, y=0)
    nodes.append(start_node)
    
    # 2. Create Customer Nodes
    platforms = data['algorithmBaseParamDto']['platformDtoList']
    node_map: Dict[str, int] = {'start_point': 0}
    
    current_idx = 1
    for p_dto in platforms:
        p_code = p_dto['platformCode']
        is_bonded = p_dto.get('mustFirst', False)
        
        node = Node(id=current_idx, is_bonded=is_bonded, x=0, y=0)
        
        # Attach items
        if p_code in items_by_platform:
            node.items = items_by_platform[p_code]
        
        nodes.append(node)
        node_map[p_code] = current_idx
        current_idx += 1
        
    # 3. Create End Node (ID=N+1)
    end_node_idx = current_idx
    end_node = Node(id=end_node_idx, is_bonded=False, x=0, y=0)
    nodes.append(end_node)
    node_map['end_point'] = end_node_idx
        
    # 4. Construct Distance Matrix
    n_nodes = len(nodes)
    dist_matrix = np.full((n_nodes, n_nodes), float('inf')) # Initialize with inf
    np.fill_diagonal(dist_matrix, 0) # Self distance is 0
    
    dist_map = data['algorithmBaseParamDto']['distanceMap']
    
    # Helper to find index
    def get_idx(code):
        return node_map.get(code, -1)

    for key, dist in dist_map.items():
        parts = key.split('+')
        if len(parts) != 2: continue
        
        u_code, v_code = parts[0], parts[1]
        
        u_idx = get_idx(u_code)
        v_idx = get_idx(v_code)
        
        if u_idx != -1 and v_idx != -1:
            dist_matrix[u_idx][v_idx] = dist
            
    return nodes, vehicle_types, dist_matrix
