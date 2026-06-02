# TurtleBot4 — Workspace ROS2 Jazzy + YOLO + LLM

> Stack : Ubuntu 24.04 · ROS2 Jazzy · NVIDIA GPU · YOLOv8n · Llama 3.2:3b (Ollama)

---

## Structure du projet

```
rise-turtlebot4-cloud-agent/
├── .gitignore
├── README.md
├── agent/
│   ├── Dockerfile
│   ├── agent_cloud.py
│   ├── fsm.py
│   ├── toolbox.py
│   └── requirements.txt   ← websockets, openai, numpy
└── web_server/
    ├── Dockerfile
    ├── web_server.py
    ├── templates/
    │   └── index.html     ← Ton interface de dashboard
    └── requirements.txt   ← fastapi, uvicorn
```

---

## 1. Prérequis selon OS

### Ubuntu (recommandé)
- Docker Engine : https://docs.docker.com/engine/install/ubuntu/
- NVIDIA Container Toolkit : https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
- Autoriser l'affichage GUI : `xhost +local:docker`

### Windows
- Docker Desktop avec WSL2 activé
- WSLg pour l'affichage GUI (Windows 11 requis pour RViz)
- Pilotes NVIDIA pour WSL2

### Mac
- Docker Desktop
- ⚠️ Pas de support NVIDIA GPU sur Mac
- XQuartz pour l'affichage GUI (`brew install --cask xquartz`)

---

## 2. Premier lancement (une seule fois)

```bash
# Cloner le dépôt
git clone https://github.com/Jimhtc/tb4.git
cd tb4_ws

# Télécharger le modèle YOLO (pas versionné sur git)
mkdir -p models
cd models
wget https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt
cd ..

# Construire l'image Docker (prend 10-20 min la première fois)
docker compose build

# Lancer le container
docker compose up -d
```

---

## 3. Utilisation quotidienne

```bash
# Démarrer le container
docker compose up -d

# Ouvrir un terminal DANS le container
docker exec -it tb4_container bash

# Depuis l'intérieur, compiler le workspace ROS2
cd /tb4_ws
colcon build --symlink-install
source install/setup.bash

# Arrêter le container
docker compose down
```

---

## 4. Travailler sur le code

Le dossier `src/` est monté en volume : **toute modification sur son PC est instantanément visible dans le container**, sans rebuild.

```bash
# Sur SON PC (pas dans le container) :
cd tb4_ws/src
# → crée tes packages ROS2 ici

# Dans le container, recompile :
colcon build --symlink-install
```

---

## 5. Ollama / LLM (sur l'ordinateur de l'université)

Ollama tourne **directement sur l'hôte**, pas dans le container.

```bash
# Sur l'ordinateur de l'université (hors Docker) :
ollama serve            # démarrer le serveur
ollama run llama3.2:3b  # télécharger + lancer le modèle

# Depuis le container, appeler l'API :
curl http://host.docker.internal:11434/api/generate \
  -d '{"model":"llama3.2:3b","prompt":"Bonjour"}'
```

En Python depuis le container :
```python
import requests
response = requests.post(
    "http://host.docker.internal:11434/api/generate",
    json={"model": "llama3.2:3b", "prompt": "Describe what you see", "stream": False}
)
print(response.json()["response"])
```

---

## 6. Workflow Git équipe

```bash
# Avant de commencer à coder
git pull origin main

# Après avoir codé
git add src/
git commit -m "feat: description de ce que tu as ajouté"
git push origin main
```

> ⚠️ Ne jamais commiter le dossier `build/`, `install/`, `log/`, ni les fichiers `.pt`

---

## 7. Variables importantes

| Variable | Valeur | Rôle |
|---|---|---|
| `ROS_DOMAIN_ID` | 42 | Isoler le réseau ROS2 de l'équipe |
| `OLLAMA_HOST` | host.docker.internal:11434 | Accès au LLM depuis le container |
| `DISPLAY` | :0 | Affichage RViz / GUI |

---

## 8. Commandes ROS2 utiles

```bash
# Voir les topics actifs
ros2 topic list

# Voir l'image caméra
ros2 run image_view image_view --ros-args -r /image:=/oakd/rgb/preview/image_raw

# Lancer la navigation
ros2 launch turtlebot4_navigation nav2.launch.py

# Lancer SLAM
ros2 launch turtlebot4_slam slam.launch.py

# Lancer RViz
ros2 launch turtlebot4_viz view_robot.launch.py
```
