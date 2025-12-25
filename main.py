from fastapi import FastAPI, Request, File, UploadFile, Form, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles # <--- ADDED THIS IMPORT
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

# --- 1. MOUNT THE SAVEETHA CLIENT FOLDER ---
# This makes CSS/JS/Images inside templates/clients/saveetha accessible
app.mount("/saveetha_files", StaticFiles(directory="templates/clients/saveetha"), name="saveetha_files")


# --- MongoDB Connection ---
MONGO_URI = "mongodb+srv://haripriyaks13_db_user:vanihari123@traceletcluster.tuizrqx.mongodb.net/?appName=traceletcluster"
client = MongoClient(MONGO_URI)
db = client["traceletDB"]

# Collections
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
    maps = list(maps_collection.find({}, {"_id": 0, "map_name": 1}))
    return templates.TemplateResponse("index.html", {"request": request, "uploaded_maps": maps})

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
    
    # PASS EMAIL IN URL (Simple "Session" for MVP)
    return RedirectResponse(url=f"/dashboard-user?email={email}", status_code=303)


# ==========================================
#           DASHBOARD & SUBSCRIPTIONS
# ==========================================

@app.get("/dashboard-user", response_class=HTMLResponse)
def user_dashboard(request: Request, email: str):
    user = users_collection.find_one({"email": email})
    if not user:
        return RedirectResponse(url="/login-user")

    all_maps = [
        {"id": "saveetha", "name": "Saveetha Engineering College", "desc": "Navigate through Saveetha campus with ease.", "active": True},
        {"id": "rajalakshmi", "name": "Rajalakshmi Engineering College", "desc": "Campus navigation coming soon.", "active": False},
        {"id": "vrmall", "name": "VR Mall Chennai", "desc": "Shopping complex navigation coming soon.", "active": False}
    ]

    user_subs = user.get("subscribed_maps", [])
    
    return templates.TemplateResponse("dashboard-user.html", {
        "request": request,
        "user": user,
        "all_maps": all_maps,
        "user_subs": user_subs
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

# Inside main.py
@app.get("/campus-route", response_class=HTMLResponse)
def campus_route(request: Request, map: str = "saveetha", email: str = ""):
    if map == "saveetha":
        return templates.TemplateResponse("clients/saveetha/routes.html", {
            "request": request, 
            "user_email": email  # <--- Pass email to template
        })
    return RedirectResponse(url=f"/dashboard-user?email={email}")

# --- NEW ROUTE FOR DIRECTIONS PAGE ---
@app.get("/saveetha/directions", response_class=HTMLResponse)
def get_directions(request: Request, startRoom: str, endRoom: str):
    # 1. Run the Algorithm
    try:
        dist, path = multi_floor_shortest_path(startRoom, endRoom)
    except ValueError as e:
        # If error, go back to search with an error message (you can handle this better later)
        return RedirectResponse(url=f"/campus-route?error={str(e)}")

    if not path:
        return RedirectResponse(url="/campus-route?error=No path found")

    # 2. Process path for the checklist (Simple Grouping)
    # We want to know where floor changes happen.
    # Heuristic: First digit usually indicates floor (2611 -> Floor 2)
    steps = []
    current_floor = None
    
    for node in path:
        # Extract floor from the first digit of the node ID
        # (Assuming node IDs like '2611' where '2' is floor)
        # Note: Your node IDs are strings.
        floor = node[0] 
        
        if floor != current_floor:
            # Floor Switch! Add a section header
            steps.append({"type": "header", "text": f"Floor {floor}"})
            current_floor = floor
        
        # Add the step
        steps.append({"type": "step", "node": node})

    # 3. Render the new template with the data
    return templates.TemplateResponse("clients/saveetha/directions.html", {
        "request": request,
        "start": startRoom,
        "end": endRoom,
        "distance": dist,
        "steps": steps
    })

# ==========================================
#           MAP & PATHFINDING LOGIC
# ==========================================

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
    return JSONResponse({"message": "Map uploaded successfully"})


@app.get("/map-image/{map_name}")
def get_map_image(map_name: str):
    doc = maps_collection.find_one({"map_name": map_name})
    if not doc:
        raise HTTPException(404, "Map not found")
    return StreamingResponse(BytesIO(doc["file_data"]), media_type=f"image/{doc['file_type']}")


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


@app.get("/indoor-path")
def indoor_path(map_name: str, sx: int, sy: int, gx: int, gy: int):
    # ... (Your existing A* Logic for Image maps remains the same) ...
    # I have omitted the full logic block here to save space, but 
    # keep your existing function body here exactly as it was!
    return JSONResponse({"message": "Use saveetha-path for room logic"}) 


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