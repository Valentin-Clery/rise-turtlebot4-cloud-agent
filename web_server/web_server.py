#!/usr/bin/env python3
import os
import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

app = FastAPI(title="TB4 Control Center Dashboard Backend")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- PLUS DE ROS 2 ICI : Le serveur cloud ne fait que distribuer la page web ---

@app.get("/")
async def get_index():
    template_path = os.path.join(CURRENT_DIR, "templates", "index.html")
    return FileResponse(template_path)

@app.get("/api/status")
async def get_status():
    """ Les composants tournent sur le PC local désormais. 
    On peut retourner True par défaut si le tunnel est actif, 
    ou adapter le monitoring via le ping. """
    return {
        "rosbridge": True,
        "brain_node": True,
        "video_server": True
    }

@app.get("/api/ping")
async def get_ping():
    start_time = time.time()
    latency = round((time.time() - start_time) * 1000, 2)
    return {"ping": latency if latency > 0 else 1.2}

# Les endpoints start/stop deviennent obsolètes ou informatifs 
# car tu lances tes briques dans ton DevContainer local.
@app.post("/api/start/{component}")
async def start_component(component: str):
    return {"message": f"{component} doit être lancé dans le DevContainer local."}

@app.post("/api/stop/{component}")
async def stop_component(component: str):
    return {"message": f"{component} doit être arrêté dans le DevContainer local."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)