# main.py
from fastapi import FastAPI, Request, File, UploadFile, Form, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pymongo import MongoClient
from bson import Binary
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image, ImageDraw
import numpy as np
import cv2
import uuid
from heapq import heappush, heappop
from builtin import multi_floor_shortest_path



app = FastAPI()
templates = Jinja2Templates(directory="templates")

# --- MongoDB ---
MONGO_URI = "mongodb+srv://haripriyaks13_db_user:vanihari123@traceletcluster.tuizrqx.mongodb.net/?appName=traceletcluster"
client = MongoClient(MONGO_URI)
db = client["traceletDB"]
maps_collection = db["maps"]

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

def delete_expired_maps(days: int = 10):
    expiry_date = datetime.utcnow() - timedelta(days=days)
    maps_collection.delete_many({"uploaded_at": {"$lt": expiry_date}})


# ---------------------------
# Home (renders template)
# ---------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    delete_expired_maps()
    maps = list(maps_collection.find({}, {"_id": 0, "map_name": 1}))
    return templates.TemplateResponse("index.html", {"request": request, "uploaded_maps": maps})


# ---------------------------
# Upload map
# ---------------------------
@app.post("/upload-map")
async def upload_map(file: UploadFile = File(...), map_name: str = Form(None)):
    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return JSONResponse({"error": "Invalid file type"}, status_code=400)

    data = await file.read()
    doc = {
        "map_name": map_name or file.filename,
        "file_data": Binary(data),
        "file_type": ext,
        "uploaded_at": datetime.utcnow()
    }
    maps_collection.insert_one(doc)
    print(f"[upload] saved map: {doc['map_name']}")
    return JSONResponse({"message": "Map uploaded successfully"})


# ---------------------------
# Serve raw map image
# ---------------------------
@app.get("/map-image/{map_name}")
def get_map_image(map_name: str):
    doc = maps_collection.find_one({"map_name": map_name})
    if not doc:
        raise HTTPException(404, "Map not found")
    return StreamingResponse(BytesIO(doc["file_data"]), media_type=f"image/{doc['file_type']}")


# ---------------------------
# Helper: find nearest walkable pixel (BFS expansion)
# ---------------------------
def find_nearest_walkable(walkable: np.ndarray, x: int, y: int, max_radius=200):
    h, w = walkable.shape
    if 0 <= x < w and 0 <= y < h and walkable[y, x]:
        return (x, y)
    for r in range(1, max_radius+1):
        x0 = max(0, x - r)
        x1 = min(w - 1, x + r)
        y0 = max(0, y - r)
        y1 = min(h - 1, y + r)
        for xi in range(x0, x1+1):
            for yi in (y0, y1):
                if walkable[yi, xi]:
                    return (xi, yi)
        for yi in range(max(y0+1, y - r + 1), min(y1, y + r - 1)+1):
            for xi in (x0, x1):
                if walkable[yi, xi]:
                    return (xi, yi)
    return None


# ---------------------------
# Indoor A* pathfinding endpoint
# ---------------------------
@app.get("/indoor-path")
def indoor_path(map_name: str, sx: int, sy: int, gx: int, gy: int):

    print(f"[indoor-path] request map={map_name} start=({sx},{sy}) goal=({gx},{gy})")
    doc = maps_collection.find_one({"map_name": map_name})
    if not doc:
        raise HTTPException(status_code=404, detail="Map not found")

    try:
        pil_img = Image.open(BytesIO(doc["file_data"])).convert("RGB")
    except Exception as e:
        print("[indoor-path] failed to open image:", e)
        raise HTTPException(status_code=500, detail="Failed to open image")

    width, height = pil_img.size
    print(f"[indoor-path] image size = {width}x{height}")

    cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

    # ---------- BETTER PREPROCESSING ----------
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

    # Remove text & small noise
    blur = cv2.medianBlur(gray, 5)

    # Adaptive threshold (handles text & uneven lighting)
    th = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        5
    )

    # Ensure white = walkable
    if np.mean(th == 255) < 0.5:
        th = cv2.bitwise_not(th)


    # ---------- PATCH 1 ----------
    kernel = np.ones((3,3), np.uint8)
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel, iterations=1)
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel, iterations=2)
    walkable = (th == 255).astype(np.uint8)

    print("[indoor-path] walkable pixels:", int(np.sum(walkable)), "of", walkable.size)

    sx = int(min(max(0, sx), width - 1))
    sy = int(min(max(0, sy), height - 1))
    gx = int(min(max(0, gx), width - 1))
    gy = int(min(max(0, gy), height - 1))

    if not walkable[sy, sx]:
        nearest = find_nearest_walkable(walkable, sx, sy, max_radius=200)
        if nearest is None:
            return JSONResponse({"error": "Start point is not on walkable area"})
        print(f"[indoor-path] snapped start {sx,sy} -> {nearest}")
        sx, sy = nearest

    if not walkable[gy, gx]:
        nearest = find_nearest_walkable(walkable, gx, gy, max_radius=200)
        if nearest is None:
            return JSONResponse({"error": "Goal point is not on walkable area"})
        print(f"[indoor-path] snapped goal {gx,gy} -> {nearest}")
        gx, gy = nearest

    # ---------- PATCH 3 ----------
    h, w = walkable.shape
    mask = np.zeros((h+2, w+2), np.uint8)
    reachable = walkable.copy()
    cv2.floodFill(reachable, mask, (sx, sy), 2)

    if reachable[gy, gx] != 2:
        noise_kernel = np.ones((2,2), np.uint8)
        walkable = cv2.morphologyEx(walkable, cv2.MORPH_OPEN, noise_kernel)

    # -------- A* begins ----------
    start = (sx, sy)
    goal = (gx, gy)

    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    open_heap = []
    heappush(open_heap, (0 + heuristic(start, goal), 0, start))
    came_from = {start: None}
    cost_so_far = {start: 0}

    visited = set()
    max_iters = width * height
    iters = 0

    neighbors_delta = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]

    found = False
    while open_heap and iters < max_iters:
        _, cur_cost, current = heappop(open_heap)
        iters += 1
        if current in visited:
            continue
        visited.add(current)

        if current == goal:
            found = True
            print(f"[indoor-path] reached goal in {iters} iterations")
            break

        x, y = current
        for dx, dy in neighbors_delta:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            if not walkable[ny, nx]:
                continue

            # ---------- PATCH 2 ----------
            if dx != 0 and dy != 0:
                if walkable[y][x+dx] == 0 and walkable[y+dy][x] == 0:
                    continue

            new_cost = cost_so_far[current] + (1.4 if dx != 0 and dy != 0 else 1.0)
            neighbor = (nx, ny)
            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost
                priority = new_cost + heuristic(neighbor, goal)
                heappush(open_heap, (priority, new_cost, neighbor))
                came_from[neighbor] = current

    if not found:
        print("[indoor-path] No path found")
        return JSONResponse({"error": "No path found between the selected points."})

    path = []
    cur = goal
    while cur is not None:
        path.append(cur)
        cur = came_from.get(cur)
    path.reverse()

    print(f"[indoor-path] path length (pixels): {len(path)}")

    draw = ImageDraw.Draw(pil_img)

    if len(path) > 0:
        ds = 1
        if len(path) > 20000:
            ds = len(path) // 20000 + 1
        for i in range(1, len(path), ds):
            p0 = path[i-1]
            p1 = path[i]
            draw.line([p0, p1], fill=(255, 0, 0),
                      width=max(3, int(min(width, height) * 0.006)))

    r = max(6, int(min(width, height) * 0.01))
    draw.ellipse((sx-r, sy-r, sx+r, sy+r), fill=(0, 200, 0))
    draw.ellipse((gx-r, gy-r, gx+r, gy+r), fill=(200, 0, 0))

    out = BytesIO()
    pil_img.save(out, format="PNG")
    out.seek(0)
    print("[indoor-path] returning annotated image")

    return StreamingResponse(out, media_type="image/png")
# ---------------------------
# Saveetha Engineering College – Room-based Path
# ---------------------------
@app.get("/saveetha-path")
def saveetha_path(start_room: str, end_room: str):
    print(f"[saveetha-path] {start_room} -> {end_room}")

    try:
        dist, path = multi_floor_shortest_path(start_room, end_room)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not path:
        raise HTTPException(status_code=404, detail="No path found")

    return {
        "distance": dist,
        "path": path
    }
