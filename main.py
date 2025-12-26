from fastapi import FastAPI, Request, File, UploadFile, Form, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
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

# --- MOUNT STATIC FILES ---
app.mount("/saveetha_files", StaticFiles(directory="templates/clients/saveetha"), name="saveetha_files")
# If you have a 'static' folder, uncomment the next line. If not, keep it commented to avoid errors.
# app.mount("/static", StaticFiles(directory="static"), name="static")

# --- MongoDB Connection ---
MONGO_URI = "mongodb+srv://haripriyaks13_db_user:vanihari123@traceletcluster.tuizrqx.mongodb.net/?appName=traceletcluster"
client = MongoClient(MONGO_URI)
db = client["traceletDB"]
maps_collection = db["maps"]
users_collection = db["users"]  

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

def delete_expired_maps(days: int = 10):
    expiry_date = datetime.utcnow() - timedelta(days=days)
    maps_collection.delete_many({"uploaded_at": {"$lt": expiry_date}})


# ==========================================
#              CORE ROUTES
# ==========================================

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    delete_expired_maps()
    # Fetch public maps for landing page demo
    public_maps = list(maps_collection.find({"owner": None}, {"_id": 0, "map_name": 1}))
    return templates.TemplateResponse("index.html", {"request": request, "uploaded_maps": public_maps})

@app.get("/login-user", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login-user.html", {"request": request})

@app.get("/signup-user", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse("signup-user.html", {"request": request})

# ==========================================
#           AUTHENTICATION LOGIC
# ==========================================

@app.post("/register")
async def register(username: str = Form(...), email: str = Form(...), password: str = Form(...)):
    if users_collection.find_one({"email": email}):
        return JSONResponse({"error": "Email already registered"}, status_code=400)
    
    user_data = {
        "username": username,
        "email": email,
        "password": password, 
        "subscribed_maps": [], 
        "created_at": datetime.utcnow()
    }
    users_collection.insert_one(user_data)
    return RedirectResponse(url="/login-user", status_code=303)

@app.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    user = users_collection.find_one({"email": email})
    if not user or user["password"] != password:
        return JSONResponse({"error": "Invalid email or password"}, status_code=401)
    
    return RedirectResponse(url=f"/dashboard-user?email={email}", status_code=303)
# ==========================================
#           ADMIN AUTH & DASHBOARD
# ==========================================

@app.get("/signup-admin", response_class=HTMLResponse)
def signup_admin_page(request: Request):
    return templates.TemplateResponse("signup-admin.html", {"request": request})

@app.get("/login-admin", response_class=HTMLResponse)
def login_admin_page(request: Request):
    return templates.TemplateResponse("login-admin.html", {"request": request})

# 1. REGISTER ADMIN
@app.post("/register-admin")
async def register_admin(
    admin_name: str = Form(...),
    email: str = Form(...), 
    password: str = Form(...),
    org_name: str = Form(...)
):
    # Check if exists
    if users_collection.find_one({"email": email}):
         return JSONResponse({"error": "Admin Email already registered"}, status_code=400)

    # Save Admin Data
    admin_data = {
        "username": admin_name,
        "email": email,
        "password": password,
        "role": "admin",
        "org_name": org_name,
        "created_at": datetime.utcnow()
    }
    users_collection.insert_one(admin_data)
    
    return RedirectResponse(url=f"/dashboard-admin?email={email}", status_code=303)

# 2. LOGIN ADMIN
@app.post("/auth-admin")
async def auth_admin(email: str = Form(...), password: str = Form(...)):
    user = users_collection.find_one({"email": email})
    
    # Simple check (In real app, check role="admin" too)
    if not user or user["password"] != password:
        return JSONResponse({"error": "Invalid admin credentials"}, status_code=401)
        
    return RedirectResponse(url=f"/dashboard-admin?email={email}", status_code=303)

# 3. ADMIN DASHBOARD
@app.get("/dashboard-admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, email: str):
    # Fetch Admin Details
    admin = users_collection.find_one({"email": email})
    if not admin:
        return RedirectResponse(url="/login-admin")

    # Fetch Maps Owned by this Admin
    my_maps = list(maps_collection.find({"owner": email}, {"_id": 0, "map_name": 1}))

    return templates.TemplateResponse("dashboard-admin.html", {
        "request": request,
        "admin_email": email,
        "org_name": admin.get("org_name", "Facility"),
        "maps": my_maps
    })
# ==========================================
#           DASHBOARD & SUBSCRIPTIONS
# ==========================================

@app.get("/dashboard-user", response_class=HTMLResponse)
def user_dashboard(request: Request, email: str):
    user = users_collection.find_one({"email": email})
    if not user:
        return RedirectResponse(url="/login-user")

    # 1. Standard Subscription Maps
    all_maps = [
        {"id": "saveetha", "name": "Saveetha Engineering College", "desc": "Navigate through Saveetha campus with ease.", "active": True},
        {"id": "rajalakshmi", "name": "Rajalakshmi Engineering College", "desc": "Campus navigation coming soon.", "active": False},
        {"id": "vrmall", "name": "VR Mall Chennai", "desc": "Shopping complex navigation coming soon.", "active": False}
    ]
    user_subs = user.get("subscribed_maps", [])

    # 2. Custom Uploaded Maps
    custom_maps = list(maps_collection.find({"owner": email}, {"_id": 0, "map_name": 1, "uploaded_at": 1}))
    
    return templates.TemplateResponse("dashboard-user.html", {
        "request": request,
        "user": user,
        "all_maps": all_maps,
        "user_subs": user_subs,
        "custom_maps": custom_maps
    })

@app.post("/subscribe")
async def subscribe(email: str = Form(...), map_id: str = Form(...)):
    users_collection.update_one(
        {"email": email},
        {"$addToSet": {"subscribed_maps": map_id}} 
    )
    return RedirectResponse(url=f"/dashboard-user?email={email}", status_code=303)


# ==========================================
#           CAMPUS NAVIGATION ROUTES
# ==========================================

@app.get("/campus-route", response_class=HTMLResponse)
def campus_route(request: Request, map: str = "saveetha", email: str = ""):
    if map == "saveetha":
        return templates.TemplateResponse("clients/saveetha/routes.html", {
            "request": request, 
            "user_email": email 
        })
    return RedirectResponse(url=f"/dashboard-user?email={email}")

@app.get("/saveetha/directions", response_class=HTMLResponse)
def get_directions(request: Request, startRoom: str, endRoom: str):
    try:
        dist, path = multi_floor_shortest_path(startRoom, endRoom)
    except ValueError as e:
        return RedirectResponse(url=f"/campus-route?error={str(e)}")

    if not path:
        return RedirectResponse(url="/campus-route?error=No path found")

    steps = []
    current_floor = None
    for node in path:
        floor = node[0] 
        if floor != current_floor:
            steps.append({"type": "header", "text": f"Floor {floor}"})
            current_floor = floor
        steps.append({"type": "step", "node": node})

    return templates.TemplateResponse("clients/saveetha/directions.html", {
        "request": request,
        "start": startRoom,
        "end": endRoom,
        "distance": dist,
        "steps": steps
    })

# ==========================================
#           IMAGE PATHFINDING UI
# ==========================================

@app.get("/image-nav", response_class=HTMLResponse)
def image_nav_page(request: Request, map_name: str, email: str = ""):
    return templates.TemplateResponse("image_nav.html", {
        "request": request,
        "map_name": map_name,
        "email": email
    })

# ==========================================
#           MAP & PATHFINDING LOGIC
# ==========================================

@app.post("/upload-map")
async def upload_map(file: UploadFile = File(...), map_name: str = Form(None), owner_email: str = Form(None),role: str = Form("user")):

    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return JSONResponse({"error": "Invalid file type"}, status_code=400)

    data = await file.read()
    unique_name = map_name or f"{uuid.uuid4().hex[:8]}_{file.filename}"
    
    doc = {
        "map_name": unique_name,
        "file_data": Binary(data),
        "file_type": ext,
        "owner": owner_email,
        "uploaded_at": datetime.utcnow()
    }
    maps_collection.insert_one(doc)
    
    # --- REDIRECT LOGIC FIXED ---
    if role == "admin":
        # If Admin uploaded it, go back to Admin Dash
        return RedirectResponse(url=f"/dashboard-admin?email={owner_email}", status_code=303)
    elif owner_email:
        # If User uploaded it, go back to User Dash
        return RedirectResponse(url=f"/dashboard-user?email={owner_email}", status_code=303)
    else:
        # If Guest (Landing Page), go to Tool
        return RedirectResponse(url=f"/image-nav?map_name={unique_name}", status_code=303)

@app.get("/map-image/{map_name}")
def get_map_image(map_name: str):
    doc = maps_collection.find_one({"map_name": map_name})
    if not doc:
        raise HTTPException(404, "Map not found")
    return StreamingResponse(BytesIO(doc["file_data"]), media_type=f"image/{doc['file_type']}")


# --- A* Algorithm Helpers ---

def find_nearest_walkable(walkable: np.ndarray, x: int, y: int, max_radius=200):
    h, w = walkable.shape
    # Check if current point is walkable
    if 0 <= x < w and 0 <= y < h and walkable[y, x]:
        return (x, y)
    
    # Spiral/Square search outwards
    for r in range(1, max_radius + 1):
        x0 = max(0, x - r); x1 = min(w - 1, x + r)
        y0 = max(0, y - r); y1 = min(h - 1, y + r)
        
        # Check top and bottom edges
        for xi in range(x0, x1 + 1):
            if walkable[y0, xi]: return (xi, y0)
            if walkable[y1, xi]: return (xi, y1)
            
        # Check left and right edges
        for yi in range(y0 + 1, y1):
            if walkable[yi, x0]: return (x0, yi)
            if walkable[yi, x1]: return (x1, yi)
            
    return None

# --- A* MAIN LOGIC ---
# Updated to accept FLOAT coordinates to prevent 422 Errors
@app.get("/indoor-path")
def indoor_path(map_name: str, sx: float, sy: float, gx: float, gy: float):
    # 1. Fetch Map
    doc = maps_collection.find_one({"map_name": map_name})
    if not doc: 
        return JSONResponse({"error": "Map not found"}, status_code=404)

    # 2. Convert to OpenCV
    try:
        pil_img = Image.open(BytesIO(doc["file_data"])).convert("RGB")
    except:
        return JSONResponse({"error": "Image error"}, status_code=500)

    width, height = pil_img.size
    cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

    # 3. Preprocessing (Walls vs Paths)
    blur = cv2.medianBlur(gray, 5)
    th = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 5)
    
    # Invert if majority is white (assuming white = empty space/walkable)
    # Actually, usually AdaptiveThreshold makes text/walls black and bg white.
    # We want Walkable = 255 (White).
    if np.mean(th == 255) < 0.5: 
        th = cv2.bitwise_not(th) 

    # Clean noise
    kernel = np.ones((3,3), np.uint8)
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel, iterations=1)
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel, iterations=2)
    walkable = (th == 255).astype(np.uint8)

    # 4. Snap Coordinates (Convert Float to Int here)
    sx_i, sy_i = int(min(max(0, sx), width-1)), int(min(max(0, sy), height-1))
    gx_i, gy_i = int(min(max(0, gx), width-1)), int(min(max(0, gy), height-1))

    # 

    if not walkable[sy_i, sx_i]: 
        snapped = find_nearest_walkable(walkable, sx_i, sy_i)
        if snapped: sx_i, sy_i = snapped
    
    if not walkable[gy_i, gx_i]: 
        snapped = find_nearest_walkable(walkable, gx_i, gy_i)
        if snapped: gx_i, gy_i = snapped

    # 5. A* Execution
    start, goal = (sx_i, sy_i), (gx_i, gy_i)
    
    # Heuristic: Manhattan
    def heuristic(a, b): return abs(a[0]-b[0]) + abs(a[1]-b[1])

    open_heap = []
    heappush(open_heap, (0 + heuristic(start, goal), 0, start))
    came_from = {start: None}
    cost_so_far = {start: 0}
    
    found = False
    iters = 0
    max_iters = 100000 

    while open_heap and iters < max_iters:
        _, current_cost, current = heappop(open_heap)
        iters += 1

        if current == goal:
            found = True
            break

        x, y = current
        # 8-direction movement
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1), (-1,-1),(1,1),(1,-1),(-1,1)]: 
            nx, ny = x + dx, y + dy
            
            if 0 <= nx < width and 0 <= ny < height and walkable[ny, nx]:
                move_cost = 1.4 if dx != 0 and dy != 0 else 1.0
                new_cost = cost_so_far[current] + move_cost
                
                if new_cost < cost_so_far.get((nx, ny), float('inf')):
                    cost_so_far[(nx, ny)] = new_cost
                    priority = new_cost + heuristic((nx, ny), goal)
                    heappush(open_heap, (priority, new_cost, (nx, ny)))
                    came_from[(nx, ny)] = current

    if not found: 
        return JSONResponse({"error": "No path found"}, status_code=400) # 400 Bad Request

    # 6. Reconstruct & Draw
    path = []
    cur = goal
    while cur:
        path.append(cur)
        cur = came_from.get(cur)
    
    draw = ImageDraw.Draw(pil_img)
    if len(path) > 1:
        draw.line(path, fill=(255, 0, 0), width=4)
        r = 6
        draw.ellipse((sx_i-r, sy_i-r, sx_i+r, sy_i+r), fill=(0, 255, 0)) # Start Green
        draw.ellipse((gx_i-r, gy_i-r, gx_i+r, gy_i+r), fill=(0, 0, 255)) # End Blue

    out = BytesIO()
    pil_img.save(out, format="PNG")
    out.seek(0)
    return StreamingResponse(out, media_type="image/png")


# Saveetha Engineering College – Room-based Path
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)