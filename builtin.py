from floors import floor1, floor2, floor3, floor4, floor5
import heapq
FLOORS = {"1": floor1, "2": floor2, "3": floor3, "4": floor4, "5": floor5}
LIFTS = ["1", "2", "3", "4"]

# ---------------- Pathfinding ----------------
def shortest_path(graph, start, goal):
    pq = [(0, start, [])]
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

def get_floor_num(room): return room[0]

def nearest_lift(graph, start, floor_num):
    best = (float("inf"), None, [])
    for lift in LIFTS:
        lift_node = floor_num + lift
        if lift_node in graph:
            dist, path = shortest_path(graph, start, lift_node)
            if dist < best[0]:
                best = (dist, lift_node, path)
    return best

def multi_floor_shortest_path(start, goal):
    start_floor = get_floor_num(start)
    goal_floor = get_floor_num(goal)
    if start_floor == goal_floor:
        return shortest_path(FLOORS[start_floor], start, goal)

    g1 = FLOORS[start_floor]
    d1, lift_start, path1 = nearest_lift(g1, start, start_floor)
    if not lift_start:
        raise ValueError(f"No lifts available on floor {start_floor}")
    lift_id = lift_start[1:]
    lift_dest = goal_floor + lift_id
    g2 = FLOORS[goal_floor]
    d2, path2 = shortest_path(g2, lift_dest, goal)
    if d2 == float("inf"):
        raise ValueError(f"No path from lift {lift_dest} to {goal} on floor {goal_floor}")
    return d1 + d2, path1 + path2[1:]

