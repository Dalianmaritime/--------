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
    # Index 0 is reserved for Start/End point
    node_map: Dict[str, int] = {'start_point': 0, 'end_point': 0} 
    nodes: List[Node] = []
    
    # Create Depot Node (ID=0)
    depot = Node(id=0, is_bonded=False, x=0, y=0) # Coordinates are dummy, we use dist matrix
    nodes.append(depot)
    
    # Create Customer Nodes
    # Use platformDtoList to define nodes and their bonded status
    platforms = data['algorithmBaseParamDto']['platformDtoList']
    
    for idx, p_dto in enumerate(platforms, start=1):
        p_code = p_dto['platformCode']
        is_bonded = p_dto.get('mustFirst', False)
        
        node = Node(id=idx, is_bonded=is_bonded, x=0, y=0)
        
        # Attach items
        if p_code in items_by_platform:
            node.items = items_by_platform[p_code]
        
        nodes.append(node)
        node_map[p_code] = idx
        
    # 3. Construct Distance Matrix
    n_nodes = len(nodes)
    dist_matrix = np.zeros((n_nodes, n_nodes))
    dist_map = data['algorithmBaseParamDto']['distanceMap']
    
    # The keys in dist_map are like "platform10+platform29"
    # We need to fill the matrix
    # Row 0: start_point + X
    # Col 0: X + end_point
    
    # Helper to find index
    def get_idx(code):
        return node_map.get(code, -1)

    for key, dist in dist_map.items():
        parts = key.split('+')
        if len(parts) != 2: continue
        
        u_code, v_code = parts[0], parts[1]
        
        u_idx = get_idx(u_code)
        v_idx = get_idx(v_code)
        
        # Handle start_point (source) and end_point (sink)
        # start_point maps to 0 (as source)
        # end_point maps to 0 (as sink)
        
        if u_code == 'start_point':
            if v_idx != -1:
                dist_matrix[0][v_idx] = dist
        elif v_code == 'end_point':
            if u_idx != -1:
                dist_matrix[u_idx][0] = dist
        else:
            if u_idx != -1 and v_idx != -1:
                dist_matrix[u_idx][v_idx] = dist
                
    return nodes, vehicle_types, dist_matrix
