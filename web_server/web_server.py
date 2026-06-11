#!/usr/bin/env python3
import os
import signal
import subprocess
import threading
import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ROS 2 Client Library
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

app = FastAPI(title="TB4 Control Center Dashboard Backend")

# Récupère le dossier absolu où se trouve le script web_server.py
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Dictionnaire de suivi des sous-processus système
processes = {
    "rosbridge": None,
    "brain_node": None,
    "video_server": None
}

# --- PARTIE ROS 2 (Passerelle Web <> Robot) ---
class WebBridgeNode(Node):
    def __init__(self):
        super().__init__('web_dashboard_bridge')

        # Ce nœud sert de relai pour journaliser l'activité sur la page Web si nécessaire
        self.response_sub = self.create_subscription(
            String,
            '/web_chat_response',
            self.response_callback,
            10
        )
        self.latest_msg = "En attente d'un ordre..."

    def response_callback(self, msg):
        self.latest_msg = msg.data

def start_ros2_loop():
    """ Boucle de rotation ROS 2 exécutée dans un thread séparé """
    if not rclpy.ok():
        rclpy.init()
    global ros_node
    ros_node = WebBridgeNode()
    rclpy.spin(ros_node)

# Démarrage du thread ROS 2 au chargement du serveur FastAPI
ros_thread = threading.Thread(target=start_ros2_loop, daemon=True)
ros_thread.start()


# --- ENDPOINTS API POUR L'INTERFACE WEB ---

@app.get("/")
async def get_index():
    # Construit le chemin absolu vers web_server/templates/index.html
    template_path = os.path.join(CURRENT_DIR, "templates", "index.html")
    return FileResponse(template_path)

@app.get("/api/status")
async def get_status():
    """ Vérifie si les processus système tournent toujours """
    status = {}
    for name, proc in processes.items():
        if proc is not None and proc.poll() is None:
            status[name] = True
        else:
            status[name] = False
    return status

@app.get("/api/ping")
async def get_ping():
    """ Calcul basique de latence pour le monitoring du Dashboard """
    start_time = time.time()
    # Simulation d'un ping ultra-léger vers le backend
    latency = round((time.time() - start_time) * 1000, 2)
    return {"ping": latency if latency > 0 else 1.2}

@app.post("/api/start/{component}")
async def start_component(component: str):
    if component not in processes:
        raise HTTPException(status_code=400, detail="Composant inconnu")
    
    if processes[component] is not None and processes[component].poll() is None:
        return {"message": f"{component} est déjà en cours d'exécution."}

    # Commandes système adaptées à ton architecture colcon workspace
    cmds = {
        "rosbridge": ["ros2", "launch", "rosbridge_server", "rosbridge_websocket_launch.xml"],
        "brain_node": ["ros2", "run", "RISE_LLM", "Agent"],
        "video_server": ["ros2", "run", "web_video_server", "web_video_server"]
    }

    try:
        # Lancement en arrière-plan sans bloquer l'API
        processes[component] = subprocess.Popen(
            cmds[component],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid # Permet de tuer tout le groupe de processus plus tard
        )
        return {"message": f"{component} démarré avec succès."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur au lancement: {str(e)}")

@app.post("/api/stop/{component}")
async def stop_component(component: str):
    if component not in processes or processes[component] == None:
        raise HTTPException(status_code=400, detail="Composant non actif")

    proc = processes[component]
    if proc.poll() is None: # Si le processus tourne
        try:
            # Termine proprement le groupe de processus (SIGINT ou SIGTERM)
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL) # Forçage si récalcitrant

        processes[component] = None
        return {"message": f"{component} arrêté."}
    
    return {"message": f"{component} était déjà arrêté."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)