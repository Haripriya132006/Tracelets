import heapq
from floors import floor1,floor2,floor3,floor4,floor5
def check_bidirectional(graph):
    issues = []
    for node, neighbors in graph.items():
        for neigh, w in neighbors:
            if neigh not in graph:
                issues.append(f"{node} → {neigh} exists but {neigh} not in graph")
            else:
                # Instead of checking exact tuple, check if neigh has node with same weight
                if not any(n == node and wt == w for n, wt in graph[neigh]):
                    issues.append(f"{node} → {neigh} exists but not {neigh} → {node}")
    return issues


# res=check_bidirectional(floor5)
# print(res)
# res=check_bidirectional(floor2)
# print(res)
# res=check_bidirectional(floor3)
# print(res)

def shortest_path(graph, start, goal):
    pq = [(0, start, [])]  # (distance, node, path_so_far)
    visited = set()

    while pq:
        dist, node, path = heapq.heappop(pq)
        if node in visited:
            continue
        visited.add(node)
        path = path + [node]

        if node == goal:
            return dist, path

        for neigh, w in graph.get(node, []):
            if neigh not in visited:
                heapq.heappush(pq, (dist + w, neigh, path))

    return float("inf"), []


# import heapq
# from floors import floor1, floor2

FLOORS = {
    "1": floor1,
    "2": floor2,
    "3":floor3,
    "4":floor4,
    "5":floor5,

    # add floor3, floor4 later
}

# all lift IDs (must exist on every floor)
LIFTS = ["1", "2", "3", "4"]

def get_floor_num(room):
    """First digit of room code = floor number"""
    return room[0]

def nearest_lift(graph, start, floor_num):
    """Find nearest lift node from a start room in a single floor graph"""
    best = (float("inf"), None, [])
    for lift in LIFTS:
        lift_node = floor_num + lift  # e.g. "1" + "1" = "11"
        if lift_node in graph:
            dist, path = shortest_path(graph, start, lift_node)
            if dist < best[0]:
                best = (dist, lift_node, path)
    return best  # (distance, lift_node, path)

def multi_floor_shortest_path(start, goal):
    start_floor = get_floor_num(start)
    goal_floor = get_floor_num(goal)

    if start_floor == goal_floor:
        return shortest_path(FLOORS[start_floor], start, goal)

    # Step 1: nearest lift on start floor
    g1 = FLOORS[start_floor]
    d1, lift_start, path1 = nearest_lift(g1, start, start_floor)
    if not lift_start:
        raise ValueError(f"No lifts available on floor {start_floor}")

    # Step 2: vertical travel
    lift_id = lift_start[1:]       # e.g. "11" → "1"
    lift_dest = goal_floor + lift_id   # e.g. "2" + "1" = "21"

    # Step 3: path from lift to destination on goal floor
    g2 = FLOORS[goal_floor]
    d2, path2 = shortest_path(g2, lift_dest, goal)
    if d2 == float("inf"):
        raise ValueError(f"No path from lift {lift_dest} to {goal} on floor {goal_floor}")

    total_dist = d1 + d2
    total_path = path1 + path2[1:]  # avoid duplicating lift
    return total_dist, total_path


res = multi_floor_shortest_path("1371", "5451")
print(res)
