from fastapi import FastAPI, Request, File, UploadFile, Form, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pymongo import MongoClient
from bson import Binary
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image, ImageDraw
import uuid
import urllib.parse

# If you have the built-in pathfinder, keep it; otherwise stub.
try:
    from builtin import multi_floor_shortest_path
except Exception:
    def multi_floor_shortest_path(s, g):
        raise NotImplementedError("Built-in pathfinder not available in this environment")

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# --- MongoDB setup (use your URI) ---
MONGO_URI = "mongodb+srv://haripriyaks13_db_user:vanihari123@traceletcluster.tuizrqx.mongodb.net/traceletDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client["traceletDB"]
maps_collection = db["maps"]

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "img"}

def delete_expired_maps():
    expiry_date = datetime.utcnow() - timedelta(days=10)
    maps_collection.delete_many({"uploaded_at": {"$lt": expiry_date}})

# --- Home route: render template with uploaded maps ---
@app.get("/", response_class=HTMLResponse)
def home(request: Request, response: Response):
    delete_expired_maps()
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(key="session_id", value=session_id, httponly=True)
    uploaded_maps = list(maps_collection.find({}, {"_id": 0, "map_name": 1}))
    return templates.TemplateResponse("index.html", {
        "request": request,
        "builtin_map": "Saveetha Engineering College",
        "uploaded_maps": uploaded_maps
    })

# --- Upload map ---
@app.post("/upload-map")
async def upload_map(file: UploadFile = File(...), map_name: str = Form(None)):
    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return JSONResponse({"error": "Unsupported file type"}, status_code=400)
    contents = await file.read()
    doc = {
        "map_name": map_name or file.filename,
        "file_data": Binary(contents),
        "file_type": ext,
        "uploaded_at": datetime.utcnow()
    }
    maps_collection.insert_one(doc)
    print(f"[upload] saved map: {doc['map_name']}")
    return JSONResponse({"message": f"Map '{doc['map_name']}' uploaded successfully!"})

# --- Serve raw stored map image ---
@app.get("/map-image/{map_name}")
def get_map_image(map_name: str):
    # map_name arrives URL-decoded automatically by FastAPI
    print(f"[map-image] requested map_name: {map_name}")
    doc = maps_collection.find_one({"map_name": map_name})
    if not doc or "file_data" not in doc:
        return JSONResponse({"error": "Image not found"}, status_code=404)
    # convert Binary to bytes; StreamingResponse can take BytesIO
    return StreamingResponse(BytesIO(doc["file_data"]), media_type=f"image/{doc['file_type']}")

# --- Built-in shortest path (unchanged) ---
@app.get("/shortest-path")
def get_shortest_path(start: str, goal: str):
    try:
        dist, path = multi_floor_shortest_path(start, goal)
        return JSONResponse({
            "distance": dist,
            "path": path,
            "directions": " → ".join(path)
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

# --- EXTERNAL PATH: draw on uploaded map using pixel coordinates ---
@app.get("/external-path")
def external_path(map_name: str, sx: float, sy: float, gx: float, gy: float):
    """
    Example: /external-path?map_name=MyMap.webp&sx=120.5&sy=200.3&gx=300&gy=400
    Returns PNG image with start (green), end (red), and highlighted line (yellow).
    """
    # map_name from query may be URL-encoded - FastAPI gives decoded string already
    print(f"[external-path] map_name={map_name} sx={sx} sy={sy} gx={gx} gy={gy}")

    doc = maps_collection.find_one({"map_name": map_name})
    if not doc or "file_data" not in doc:
        # Try decode variants if user used plus signs or spaces encoded differently
        alt = urllib.parse.unquote(map_name)
        if alt != map_name:
            doc = maps_collection.find_one({"map_name": alt})
    if not doc or "file_data" not in doc:
        print("[external-path] map not found in DB")
        raise HTTPException(status_code=404, detail="Map not found")

    try:
        img = Image.open(BytesIO(doc["file_data"])).convert("RGBA")
    except Exception as e:
        print(f"[external-path] error opening image: {e}")
        raise HTTPException(status_code=500, detail="Failed to open image")

    draw = ImageDraw.Draw(img)

    # Validate coordinates: they should be inside image bounds — clamp for safety
    width, height = img.size
    sx_clamped = max(0, min(width - 1, sx))
    sy_clamped = max(0, min(height - 1, sy))
    gx_clamped = max(0, min(width - 1, gx))
    gy_clamped = max(0, min(height - 1, gy))

    # Draw start (green) and end (red)
    r = max(6, int(min(width, height) * 0.01))  # radius relative to image size
    draw.ellipse((sx_clamped - r, sy_clamped - r, sx_clamped + r, sy_clamped + r), fill=(0, 200, 0, 255))
    draw.ellipse((gx_clamped - r, gy_clamped - r, gx_clamped + r, gy_clamped + r), fill=(200, 0, 0, 255))

    # Draw line (highlight) between points
    line_width = max(4, int(min(width, height) * 0.008))
    draw.line([(sx_clamped, sy_clamped), (gx_clamped, gy_clamped)], fill=(255, 215, 0, 220), width=line_width)

    # (Optional) add small circles along line for stronger visibility
    # For a straight-line highlight we can sprinkle intermediate points:
    steps = 40
    for i in range(1, steps):
        t = i / steps
        x = sx_clamped + (gx_clamped - sx_clamped) * t
        y = sy_clamped + (gy_clamped - sy_clamped) * t
        rr = max(1, int(r * 0.35))
        draw.ellipse((x-rr, y-rr, x+rr, y+rr), fill=(255, 200, 50, 200))

    # Return as PNG
    out = BytesIO()
    img.save(out, format="PNG")
    out.seek(0)
    print("[external-path] returning highlighted image")
    return StreamingResponse(out, media_type="image/png")

# --- Delete session (optional) ---
@app.post("/delete-session")
def delete_session(request: Request, response: Response):
    session_id = request.cookies.get("session_id")
    if session_id:
        maps_collection.delete_many({"session_id": session_id})
        response.delete_cookie("session_id")
        return JSONResponse({"message": "Session cleared and maps deleted."})
    return JSONResponse({"message": "No active session."})
