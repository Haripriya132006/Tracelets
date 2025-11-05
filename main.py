from fastapi import FastAPI, Request, File, UploadFile, Form, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pymongo import MongoClient
from bson import Binary
from datetime import datetime, timedelta
from io import BytesIO
import uuid
from builtin import multi_floor_shortest_path  # Your Saveetha map pathfinder

# ---------------- App Setup ----------------
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# ---------------- MongoDB Setup ----------------
MONGO_URI = "mongodb+srv://haripriyaks13_db_user:vanihari123@traceletcluster.tuizrqx.mongodb.net/traceletDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client["traceletDB"]
maps_collection = db["maps"]

print ("continue 1")

# ---------------- Config ----------------
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "img"}
print("continue 2")

# ---------------- Helpers ----------------
def delete_expired_maps():
    """Delete maps older than 10 days"""
    expiry_date = datetime.utcnow() - timedelta(days=10)
    maps_collection.delete_many({"uploaded_at": {"$lt": expiry_date}})

# ---------------- Routes ----------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request, response: Response):
    """Render home page showing available maps"""
    delete_expired_maps()

    # Handle session cookies
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


@app.get("/shortest-path")
def get_shortest_path(start: str, goal: str):
    """Run built-in Saveetha map pathfinder"""
    try:
        dist, path = multi_floor_shortest_path(start, goal)
        return JSONResponse({
            "distance": dist,
            "path": path,
            "directions": " → ".join(path)
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/upload-map")
async def upload_map(file: UploadFile = File(...), map_name: str = Form(None)):
    """Upload a map image directly to MongoDB — no session required"""
    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return JSONResponse({"error": "Unsupported file type"}, status_code=400)

    contents = await file.read()

    maps_collection.insert_one({
        "map_name": map_name or file.filename,
        "file_data": Binary(contents),
        "file_type": ext,
        "uploaded_at": datetime.utcnow(),
        # no session_id — public uploads
    })

    return JSONResponse({
        "message": f"Map '{map_name or file.filename}' uploaded successfully!"
    })



@app.get("/map-image/{map_name}")
def get_map_image(map_name: str):
    """Serve a map image stored in MongoDB"""
    doc = maps_collection.find_one({"map_name": map_name})
    if not doc or "file_data" not in doc:
        return JSONResponse({"error": "Image not found"}, status_code=404)

    return StreamingResponse(
        BytesIO(doc["file_data"]),
        media_type=f"image/{doc['file_type']}"
    )


@app.post("/delete-session")
def delete_session(request: Request, response: Response):
    """Delete all maps for this session and clear cookies"""
    session_id = request.cookies.get("session_id")
    if session_id:
        maps_collection.delete_many({"session_id": session_id})
        response.delete_cookie("session_id")
        return JSONResponse({"message": "Session cleared and maps deleted."})
    return JSONResponse({"message": "No active session."})
@app.get("/map-image/{map_name}")
def get_map_image(map_name: str):
    """Serve a map image stored in MongoDB"""
    doc = maps_collection.find_one({"map_name": map_name})
    if not doc or "file_data" not in doc:
        return JSONResponse({"error": "Image not found"}, status_code=404)

    return StreamingResponse(
        BytesIO(doc["file_data"]),
        media_type=f"image/{doc['file_type']}"
    )
