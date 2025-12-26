# Tracelets - Indoor Navigation System
> **Pin. Trace. Navigate.**

**Tracelets** is a hardware-free indoor navigation platform designed to help users navigate complex infrastructures—such as universities, hospitals, and malls—using digital blueprints. Unlike GPS, which fails indoors, Tracelets uses graph-based pathfinding algorithms to provide accurate room-to-room directions.

### 🚀 Pilot Program
This repository contains the MVP (Minimum Viable Product) featuring a fully functional pilot implementation for **Saveetha Engineering College**.

---

## 🌟 Key Features

### 1. User Hub & Dashboard
* **User Authentication:** Secure Login and Sign-Up system powered by MongoDB.
* **Dynamic Dashboard:** Manage layout subscriptions ("My Layouts") and explore new spaces.
* **Admin Portal (Prototype):** Dedicated registration flow for facility managers to register organizations.

### 2. CampusRoute Module (Saveetha Pilot)
* **Room-to-Room Navigation:** Enter a start and end room (e.g., `2611` to `Library`).
* **Multi-Floor Routing:** Automatically detects staircases/lifts and switches floor maps.
* **Step-by-Step Directions:** Generates a text-based checklist of the path.

### 3. Custom Map Tool (Image Navigation)
* **Upload Any Blueprint:** Users can upload their own floor plan images (JPG/PNG).
* **Interactive Pathfinding:** Click to set a **Start Point (Green)** and **Goal (Red)**.
* **Visual Route:** The system draws the shortest path instantly on the image using Computer Vision.

---

## 🛠️ Tech Stack

* **Frontend:** HTML5, CSS3, JavaScript (Vanilla)
* **Backend:** Python (FastAPI)
* **Database:** MongoDB (Cloud Atlas)
* **Computer Vision:** OpenCV, NumPy, Pillow (PIL)
* **Algorithms:**
    * **Dijkstra's Algorithm:** For node-based routing (Room-to-Room).
    * **A* (A-Star):** For pixel-based grid navigation (Image Drawing).

---

## 📂 Project Structure

```text
/Tracelets
  ├── main.py                 # Core Backend API & Server
  ├── builtin.py              # Dijkstra Logic (Saveetha Pilot)
  ├── floors.py               # Graph Data (Nodes & Edges)
  ├── /templates              # HTML Pages
  │     ├── index.html        # Landing Page
  │     ├── image_nav.html    # A* Image Navigation Tool
  │     ├── dashboard-user.html
  │     └── /clients/saveetha # Custom Module for Pilot Client
  ```

  ## ⚡ How to Run Locally

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/Haripriya132006/Tracelets.git](https://github.com/Haripriya132006/Tracelets.git)
    cd Tracelets
    ```

2.  **Install Dependencies**
    *(Includes FastAPI, DB, and Image Processing libraries)*
    ```bash
    pip install fastapi uvicorn pymongo python-multipart opencv-python numpy pillow aiofiles
    ```

3.  **Run the Server**
    ```bash
    python main.py
    ```

4.  **Access the App**
    Open your browser and go to: `http://127.0.0.1:8000`

---

## 🔮 Future Enhancements (Phase 2)

* **Admin Portal:** Drag-and-drop SVG upload for new facility managers.
* **Automated Graph Parsing:** Computer Vision to automatically convert floor plan images into navigable nodes.
* **Live Positioning:** Integration with geomagnetic fingerprinting for "Blue Dot" location tracking.

---

**Developed by:** Haripriya & Sajetha
**Institution:** Saveetha Engineering College